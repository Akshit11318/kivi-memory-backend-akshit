"""Inference orchestration: Gate -> Retrieve -> Align(ASR,formatted) -> Decide ->
Produce -> Trace. One place. Never positional token index.
"""

from __future__ import annotations

import time

from kivi_memory.decide.conservative import decide_token
from kivi_memory.domain.models import RunTrace, TokenDecision
from kivi_memory.learner.align import content_window, normalize_word
from kivi_memory.pipeline.align import align_formatted_to_asr, match_keys, tokenize
from kivi_memory.produce import passthrough, rewrite
from kivi_memory.retrieve import exact, phonetic
from kivi_memory.store.db import MemoryStore

_RETRIEVERS = {"exact": exact.retrieve, "phonetic": phonetic.retrieve}
_IMPLEMENTED_PROFILES = ("off", "exact", "phonetic")


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
    formatted_cores_raw = [t.core for t in formatted_tokens]
    retriever = _RETRIEVERS[profile]

    decisions: list[TokenDecision] = []
    memories_used: set[int] = set()

    for index, token in enumerate(formatted_tokens):
        surfaces = set(match_keys(token))
        for asr_index in alignment.get(index, []):
            surfaces.add(asr_tokens_norm[asr_index])

        candidates = retriever(store, user_id, surfaces)
        window = content_window(formatted_cores_raw, index)
        result = decide_token(token.core, candidates, window)

        matched_surface = None
        if result.memory is not None:
            matched_surface = next((s for s in surfaces if s in result.memory.forms), None)
            memories_used.add(result.memory.id)

        decisions.append(
            TokenDecision(
                index=index,
                token=token.core,
                decision=result.decision,
                reason=result.reason,
                canonical=result.memory.canonical if result.memory else None,
                memory_ids=tuple(m.id for m in candidates),
                matched_surface=matched_surface,
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
    )
