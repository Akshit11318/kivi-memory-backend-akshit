"""Learner, Retriever, Decider, Producer protocols. One job, one contract per slot."""

from __future__ import annotations

from typing import Protocol, Sequence

from kivi_memory.domain.models import Memory, Observation, TokenDecision
from kivi_memory.store.db import MemoryStore


class Learner(Protocol):
    """Observation -> memory upsert or no-op."""

    def observe(self, store: MemoryStore, observation: Observation) -> Memory | None: ...


class Retriever(Protocol):
    """Text + store -> candidate memories that might be relevant."""

    def retrieve(
        self,
        store: MemoryStore,
        user_id: str,
        asr_tokens: Sequence[str],
        formatted_tokens: Sequence[str],
    ) -> Sequence[Memory]: ...


class Decider(Protocol):
    """Aligned formatted tokens -> per-token APPLY|ABSTAIN."""

    def decide(
        self, formatted_tokens: Sequence[str], candidates: Sequence[Memory]
    ) -> list[TokenDecision]: ...


class Producer(Protocol):
    """Formatted + decisions -> the third transcript (memory-aware text)."""

    def produce(
        self, formatted_tokens: Sequence[str], decisions: Sequence[TokenDecision]
    ) -> str: ...
