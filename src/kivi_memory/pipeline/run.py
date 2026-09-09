"""Inference orchestration: Retrieve(cascade) -> Align(ASR,formatted) ->
cheap doors -> one LLM call for the whole sentence -> Produce -> Trace.

Two passes: cheap doors first; whatever is still pending is numbered in
the sentence and scored in a single HTTP call (every memory, every
repeat). One loop shape, one place the retriever is chosen. Never
positional token index.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from kivi_memory.config import DEFAULT_DECIDE
from kivi_memory.decide.conservative import cheap_gate
from kivi_memory.decide.llm_helper import decide_sentence
from kivi_memory.domain.models import Memory, RunTrace, TokenDecision
from kivi_memory.learner.align import normalize_word
from kivi_memory.pipeline.align import align_formatted_to_asr, mark_occurrences, match_keys, tokenize
from kivi_memory.produce import passthrough, rewrite
from kivi_memory.retrieve import exact, phonetic
from kivi_memory.store.db import MemoryStore

_IMPLEMENTED_PROFILES = ("off", "exact", "phonetic", "auto")


def _retrieve(profile: str, store: MemoryStore, user_id: str, surfaces: set[str]) -> tuple[list[Memory], str | None]:
    """The one place a retriever is chosen. `exact` and `phonetic` force a
    single retriever (ablation); `auto` (and any other live profile) cascades
    exact then phonetic — exact always wins when the surface is already a
    stored form."""
    if profile == "exact":
        candidates = exact.retrieve(store, user_id, surfaces)
        return candidates, ("exact" if candidates else None)
    if profile == "phonetic":
        candidates = phonetic.retrieve(store, user_id, surfaces)
        return candidates, ("phonetic" if candidates else None)

    candidates = exact.retrieve(store, user_id, surfaces)
    if candidates:
        return candidates, "exact"
    candidates = phonetic.retrieve(store, user_id, surfaces)
    return candidates, ("phonetic" if candidates else None)


@dataclass(frozen=True)
class _Pending:
    """One token that cleared the cheap doors and needs the last vote
    (`--decide llm` or `--decide ungated`). All pendings share one helper call."""

    index: int
    token_core: str
    surfaces: set[str]
    candidates: list[Memory]
    matched_via: str | None
    memory: Memory


def run(
    store: MemoryStore,
    user_id: str,
    asr: str,
    formatted: str,
    profile: str,
    decide: str = DEFAULT_DECIDE,
) -> RunTrace:
    start = time.perf_counter()

    if profile == "off":
        memory_aware = passthrough.produce(formatted)
        return RunTrace(
            asr=asr,
            formatted=formatted,
            memory_aware=memory_aware,
            profile=profile,
            decide="off",
            decisions=(),
            memories_used=(),
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    if profile not in _IMPLEMENTED_PROFILES:
        raise NotImplementedError(f"profile {profile!r} is not wired up yet")

    formatted_tokens = tokenize(formatted)
    asr_tokens_norm = [normalize_word(t) for t in asr.split()]
    formatted_core_norm = [normalize_word(t.core) for t in formatted_tokens]
    alignment = align_formatted_to_asr(asr_tokens_norm, formatted_core_norm)

    decisions_by_index: dict[int, TokenDecision] = {}
    memories_used: set[int] = set()
    total_model_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    pending: list[_Pending] = []

    for index, token in enumerate(formatted_tokens):
        surfaces = set(match_keys(token))
        for asr_index in alignment.get(index, []):
            surfaces.add(asr_tokens_norm[asr_index])

        candidates, matched_via = _retrieve(profile, store, user_id, surfaces)
        gate = cheap_gate(token.core, candidates)

        if gate.decision is not None:
            decisions_by_index[index] = TokenDecision(
                index=index,
                token=token.core,
                decision=gate.decision,
                reason=gate.reason,
                canonical=None,
                memory_ids=tuple(m.id for m in candidates),
                matched_surface=None,
                matched_via=matched_via,
            )
            continue

        memory = gate.memory
        assert memory is not None
        pending.append(_Pending(index, token.core, surfaces, candidates, matched_via, memory))

    if pending:
        marked_sentence = mark_occurrences(formatted_tokens, [item.index for item in pending])
        results = decide_sentence(
            marked_sentence,
            [(item.token_core, item.memory) for item in pending],
            decide=decide,
        )
        total_model_calls += sum(r.model_calls for r in results)
        total_prompt_tokens += sum(r.prompt_tokens or 0 for r in results)
        total_completion_tokens += sum(r.completion_tokens or 0 for r in results)

        for item, result in zip(pending, results):
            canonical = None
            matched_surface = None
            if result.decision == "APPLY":
                canonical = item.memory.canonical
                matched_surface = next((s for s in item.surfaces if s in item.memory.forms), None)
                memories_used.add(item.memory.id)

            decisions_by_index[item.index] = TokenDecision(
                index=item.index,
                token=item.token_core,
                decision=result.decision,
                reason=result.reason,
                canonical=canonical,
                memory_ids=tuple(m.id for m in item.candidates),
                matched_surface=matched_surface,
                matched_via=item.matched_via,
                helper=result.helper,
                model=result.model,
                llm_latency_ms=result.latency_ms,
                llm_score=result.score,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
            )

    decisions = [decisions_by_index[i] for i in range(len(formatted_tokens))]
    memory_aware = rewrite.produce(formatted_tokens, decisions)

    return RunTrace(
        asr=asr,
        formatted=formatted,
        memory_aware=memory_aware,
        profile=profile,
        decide=decide,
        decisions=tuple(decisions),
        memories_used=tuple(sorted(memories_used)),
        latency_ms=(time.perf_counter() - start) * 1000,
        model_calls=total_model_calls,
        prompt_tokens=total_prompt_tokens,
        completion_tokens=total_completion_tokens,
    )
