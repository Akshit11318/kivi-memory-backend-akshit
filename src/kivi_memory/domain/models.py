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

    `teach_text` is the correction sentence (or an optional example sentence
    passed to dictionary_add) kept solely as evidence for the LLM sense
    helper's prompt. It is never a token-overlap gate — decide never reads it.
    """

    id: int
    user_id: str
    canonical: str
    forms: tuple[str, ...]
    confidence: float
    created_at: str
    updated_at: str
    teach_text: str | None = None


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
    matched_via: str | None = None  # "exact" | "phonetic" | None (no candidates)
    helper: str | None = None  # "llm" | "ungated" | None (a cheap door closed first)
    model: str | None = None  # model id, only set when helper == "llm"
    llm_latency_ms: float | None = None  # only set when helper == "llm"
    llm_score: float | None = None  # raw 0-100 sense score, only set when helper == "llm"
    prompt_tokens: int | None = None  # usage for the one real call a batch made; None elsewhere
    completion_tokens: int | None = None


@dataclass(frozen=True)
class RunTrace:
    """Full inspectable run record: ASR, formatted, memory-aware, and why."""

    asr: str
    formatted: str
    memory_aware: str
    profile: str
    decide: str
    decisions: tuple[TokenDecision, ...]
    memories_used: tuple[int, ...]
    latency_ms: float
    model_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
