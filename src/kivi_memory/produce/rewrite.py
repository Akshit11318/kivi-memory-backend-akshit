"""Deterministic rewrite of APPLY tokens only. plan.md: produce.

Degenerates to passthrough automatically when nothing APPLYs — no separate
all-abstain special case needed.
"""

from __future__ import annotations

from typing import Sequence

from kivi_memory.domain.models import TokenDecision
from kivi_memory.pipeline.align import DecomposedToken, stitch


def _rewrite_core(core: str, canonical: str, matched_surface: str | None) -> str:
    if matched_surface is None or core.lower() == matched_surface:
        return canonical
    if "-" in core:
        segments = core.split("-")
        replaced_once = False
        new_segments = []
        for segment in segments:
            if not replaced_once and segment.lower() == matched_surface:
                new_segments.append(canonical)
                replaced_once = True
            else:
                new_segments.append(segment)
        if replaced_once:
            return "-".join(new_segments)
    return canonical


def produce(tokens: list[DecomposedToken], decisions: Sequence[TokenDecision]) -> str:
    cores = []
    for tok, decision in zip(tokens, decisions):
        if decision.decision == "APPLY" and decision.canonical:
            cores.append(_rewrite_core(tok.core, decision.canonical, decision.matched_surface))
        else:
            cores.append(tok.core)
    return stitch(tokens, cores)
