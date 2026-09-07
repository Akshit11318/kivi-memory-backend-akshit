"""MemoryStore migrate / upsert / list / reset."""

from pathlib import Path
from typing import Iterator

import pytest

from kivi_memory.domain.models import Observation
from kivi_memory.store.db import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    with MemoryStore(tmp_path / "kivi.sqlite") as store:
        yield store


def test_fresh_store_has_no_memories(store: MemoryStore) -> None:
    assert store.list_memories() == []


def test_upsert_inserts_new_memory(store: MemoryStore) -> None:
    memory = store.upsert_memory("demo", "Kivi", ["kivi", "kiwi"], confidence=1.0)
    assert memory.canonical == "Kivi"
    assert set(memory.forms) == {"kivi", "kiwi"}
    assert memory.confidence == 1.0
    assert store.list_memories() == [memory]


def test_upsert_same_canonical_merges_not_duplicates(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Aaditya", ["aditya"], confidence=0.85)
    merged = store.upsert_memory("demo", "Aaditya", ["adithya"], confidence=0.90)

    memories = store.list_memories()
    assert len(memories) == 1
    assert set(merged.forms) == {"aditya", "adithya"}
    assert merged.confidence == 0.90


def test_reset_wipes_memories_and_observations(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Kivi", ["kiwi"], confidence=1.0)
    store.add_observation(
        Observation(user_id="demo", source="dictionary_add", created_at="", canonical="Kivi")
    )

    store.reset()

    assert store.list_memories() == []
    assert store.list_observations() == []


def test_reset_then_reopen_is_still_empty_and_valid(tmp_path: Path) -> None:
    db_path = tmp_path / "kivi.sqlite"
    with MemoryStore(db_path) as store:
        store.upsert_memory("demo", "Kivi", ["kiwi"], confidence=1.0)
        store.reset()

    with MemoryStore(db_path) as reopened:
        assert reopened.list_memories() == []


def test_find_memory_ids_by_form_is_user_scoped(store: MemoryStore) -> None:
    a = store.upsert_memory("user_a", "Kivi", ["kivi"], confidence=1.0)
    store.upsert_memory("user_b", "Kiwi", ["kivi"], confidence=1.0)

    assert store.find_memory_ids_by_form("user_a", "kivi") == [a.id]
    assert store.find_memory_ids_by_form("user_c", "kivi") == []
