"""Inference orchestration: Retrieve(cascade) -> Align(ASR,formatted) ->
cheap doors -> LLM helper (or ungated) -> Produce -> Trace.

One loop, one place the retriever is chosen. Never positional token index.
"""

from __future__ import annotations

import time

from kivi_memory.decide.conservative import cheap_gate
from kivi_memory.decide.llm_helper import decide_with_helper
from kivi_memory.domain.models import Memory, RunTrace, TokenDecision
from kivi_memory.learner.align import normalize_word
from kivi_memory.pipeline.align import align_formatted_to_asr, match_keys, tokenize
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

    decisions: list[TokenDecision] = []
    memories_used: set[int] = set()
    total_model_calls = 0

    for index, token in enumerate(formatted_tokens):
        surfaces = set(match_keys(token))
        for asr_index in alignment.get(index, []):
            surfaces.add(asr_tokens_norm[asr_index])

        candidates, matched_via = _retrieve(profile, store, user_id, surfaces)
        gate = cheap_gate(token.core, candidates)

        helper = None
        model = None
        llm_latency_ms = None

        if gate.decision is not None:
            decision, reason, memory = gate.decision, gate.reason, None
        else:
            memory = gate.memory
            assert memory is not None
            result = decide_with_helper(formatted, token.core, memory)
            decision, reason = result.decision, result.reason
            helper, model, llm_latency_ms = result.helper, result.model, result.latency_ms
            total_model_calls += result.model_calls

        canonical = None
        matched_surface = None
        if decision == "APPLY" and memory is not None:
            canonical = memory.canonical
            matched_surface = next((s for s in surfaces if s in memory.forms), None)
            memories_used.add(memory.id)

        decisions.append(
            TokenDecision(
                index=index,
                token=token.core,
                decision=decision,
                reason=reason,
                canonical=canonical,
                memory_ids=tuple(m.id for m in candidates),
                matched_surface=matched_surface,
                matched_via=matched_via,
                helper=helper,
                model=model,
                llm_latency_ms=llm_latency_ms,
            )
        )

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
