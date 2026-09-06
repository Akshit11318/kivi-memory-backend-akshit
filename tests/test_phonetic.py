"""--profile phonetic: retrieves what exact misses, without over-firing on
short-token collisions (plan.md families 10, 21)."""

from pathlib import Path
from typing import Iterator

import pytest

from kivi_memory.pipeline.run import run
from kivi_memory.store.db import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    with MemoryStore(tmp_path / "kivi.sqlite") as store:
        yield store


def test_phonetic_finds_kiwi_when_only_kivi_stored_exact_misses(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Kivi", ["kivi"], confidence=1.0)  # "kiwi" never stored

    exact_trace = run(store, "demo", asr="", formatted="Please check the kiwi service.", profile="exact")
    assert exact_trace.memory_aware == "Please check the kiwi service."

    phonetic_trace = run(
        store, "demo", asr="", formatted="Please check the kiwi service.", profile="phonetic"
    )
    assert phonetic_trace.memory_aware == "Please check the Kivi service."


def test_phonetic_does_not_over_apply_ravi_robbie(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Ravi", ["ravi"], confidence=1.0)
    trace = run(store, "demo", asr="", formatted="Robbie joined the call.", profile="phonetic")
    assert trace.memory_aware == "Robbie joined the call."
    decision = next(d for d in trace.decisions if d.token == "Robbie")
    assert decision.decision == "ABSTAIN"


def test_phonetic_does_not_collide_kavi_covey(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Kavi", ["kavi"], confidence=1.0)
    trace = run(store, "demo", asr="", formatted="Covey led the review.", profile="phonetic")
    assert trace.memory_aware == "Covey led the review."


def test_phonetic_still_handles_ordinary_exact_matches(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Aaditya", ["aditya"], confidence=0.9)
    trace = run(store, "demo", asr="", formatted="Ask Aditya now.", profile="phonetic")
    assert trace.memory_aware == "Ask Aaditya now."
