"""Exact / normalized overlap retriever.

Word-boundary safety is structural, not a rule to enforce: this only ever
does exact dict lookups against whole normalized surfaces, never a substring
`contains` check, so `Kivi` inside `Kivimaki` can't match (family 11).
"""

from __future__ import annotations

from typing import Iterable

from kivi_memory.domain.models import Memory
from kivi_memory.store.db import MemoryStore


def retrieve(store: MemoryStore, user_id: str, surfaces: Iterable[str]) -> list[Memory]:
    seen: dict[int, Memory] = {}
    for surface in surfaces:
        if not surface:
            continue
        for memory_id in store.find_memory_ids_by_form(user_id, surface):
            if memory_id not in seen:
                memory = store.get_memory(memory_id)
                if memory is not None:
                    seen[memory_id] = memory
    return list(seen.values())
