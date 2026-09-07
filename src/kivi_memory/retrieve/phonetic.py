"""Metaphone retriever (jellyfish). Profile phonetic.

`jellyfish` only implements classic single-code Metaphone, not true Double
Metaphone's primary/secondary codes. Plain Metaphone maps `v` -> F but keeps a
pre-vocalic `w` as `W`, so `kiwi` (KW) and `kivi` (KF) do not collide by
default — even though the brief names this exact acoustic confusion as the
reason this profile exists ("Can we retrieve `kiwi` when only `Kivi` was
stored?"). We close that one named gap by also trying each surface with v<->w
swapped before encoding: a targeted fix for a real, named ASR confusion, not
a general fuzzy-phonetic matcher.

Family 21 (short-token false positive, e.g. Ravi vs Robbie) is guarded by
requiring the first letter to match. That's also what actually kills
unrelated short-token collisions like `kavi`/`covey` (both metaphone `KF`,
first letters `k`/`c`) — Ravi/Robbie (`RF`/`RB`) never even share a metaphone
key in the first place.
"""

from __future__ import annotations

from typing import Iterable

import jellyfish

from kivi_memory.domain.models import Memory
from kivi_memory.learner.align import normalize_word
from kivi_memory.store.db import MemoryStore

_MIN_SURFACE_LEN = 3


def _phonetic_keys(word: str) -> set[str]:
    if len(word) < _MIN_SURFACE_LEN:
        return set()
    keys = {jellyfish.metaphone(word)}
    if "v" in word or "w" in word:
        swapped = word.replace("v", "\0").replace("w", "v").replace("\0", "w")
        keys.add(jellyfish.metaphone(swapped))
    return {k for k in keys if k}


def retrieve(store: MemoryStore, user_id: str, surfaces: Iterable[str]) -> list[Memory]:
    query: dict[str, set[str]] = {}
    for surface in surfaces:
        surface_norm = normalize_word(surface)
        if surface_norm:
            query[surface_norm] = _phonetic_keys(surface_norm)

    if not any(query.values()):
        return []

    seen: dict[int, Memory] = {}
    for memory in store.list_memories(user_id):
        for form in memory.forms:
            form_keys = _phonetic_keys(form)
            if not form_keys:
                continue
            for surface, keys in query.items():
                if keys and (keys & form_keys) and surface[0] == form[0]:
                    seen[memory.id] = memory
    return list(seen.values())
