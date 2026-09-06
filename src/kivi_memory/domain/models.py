"""Observation, Memory, TokenDecision, RunTrace. Typed contracts only — no behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    """One teach event: dictionary_add or correction. Observation != memory."""

    user_id: str
    source: str  # "dictionary_add" | "correction"
    created_at: str
    id: int | None = None
    asr: str | None = None
    formatted: str | None = None
    final: str | None = None
    canonical: str | None = None
    forms: tuple[str, ...] = ()
    memory_id: int | None = None


@dataclass(frozen=True)
class Memory:
    """Per-user lexical belief: canonical + observed forms + confidence.

    Admission test: if deleting this row cannot change a future transcript's
    wording of a personal term, it is not this memory.

    `context_cues` is a small unioned bag of ±2 content-token neighbors seen at
    correction time (plan.md pinned contract #8) — a decide-time disambiguation
    gate for surfaces like `kiwi`/`Kivi`, not sentence memory. Empty means no
    gate: a dictionary_add with no sentence leaves it empty on purpose.
    """

    id: int
    user_id: str
    canonical: str
    forms: tuple[str, ...]
    confidence: float
    created_at: str
    updated_at: str
    context_cues: tuple[str, ...] = ()


@dataclass(frozen=True)
class TokenDecision:
    """Per-token APPLY/ABSTAIN with reason, for the inspectable trace."""

    index: int
    token: str
    decision: str  # "APPLY" | "ABSTAIN"
    reason: str
    canonical: str | None = None
    memory_ids: tuple[int, ...] = ()
    matched_surface: str | None = None


@dataclass(frozen=True)
class RunTrace:
    """Full inspectable run record: ASR, formatted, memory-aware, and why."""

    asr: str
    formatted: str
    memory_aware: str
    profile: str
    decisions: tuple[TokenDecision, ...]
    memories_used: tuple[int, ...]
    latency_ms: float
    model_calls: int = 0
