"""Inference orchestration: Retrieve(cascade) -> Align(ASR,formatted) ->
cheap doors -> LLM helper, batched per memory across one sentence -> Produce
-> Trace.

Two passes: the first resolves every token that a cheap door already
decides; the second groups the rest by memory (a repeated word gets one
batched LLM call for all its occurrences in the sentence, not one call
each) and reassembles decisions back into token order. One loop shape, one
place the retriever is chosen. Never positional token index.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from kivi_memory.decide.conservative import cheap_gate
from kivi_memory.decide.llm_helper import decide_with_helper
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
    """One token that cleared the cheap doors and needs the LLM helper (or
    ungated fallback), waiting to be grouped with same-memory occurrences."""

    index: int
    token_core: str
    surfaces: set[str]
    candidates: list[Memory]
    matched_via: str | None
    memory: Memory


def run(store: MemoryStore, user_id: str, asr: str, formatted: str, profile: str) -> RunTrace:
    start = time.perf_counter()

    if profile == "off":
        memory_aware = passthrough.produce(formatted)
        return RunTrace(
            asr=asr,
            formatted=formatted,
            memory_aware=memory_aware,
            profile=profile,
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
    pending_by_memory: dict[int, list[_Pending]] = {}

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
        pending_by_memory.setdefault(memory.id, []).append(
            _Pending(index, token.core, surfaces, candidates, matched_via, memory)
        )

    for group in pending_by_memory.values():
        memory = group[0].memory
        indices = [item.index for item in group]
        marked_sentence = mark_occurrences(formatted_tokens, indices)
        results = decide_with_helper(marked_sentence, group[0].token_core, memory, len(group))
        total_model_calls += sum(r.model_calls for r in results)

        for item, result in zip(group, results):
            canonical = None
            matched_surface = None
            if result.decision == "APPLY":
                canonical = memory.canonical
                matched_surface = next((s for s in item.surfaces if s in memory.forms), None)
                memories_used.add(memory.id)

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
            )

    decisions = [decisions_by_index[i] for i in range(len(formatted_tokens))]
    memory_aware = rewrite.produce(formatted_tokens, decisions)

    return RunTrace(
        asr=asr,
        formatted=formatted,
        memory_aware=memory_aware,
        profile=profile,
        decisions=tuple(decisions),
        memories_used=tuple(sorted(memories_used)),
        latency_ms=(time.perf_counter() - start) * 1000,
        model_calls=total_model_calls,
    )
