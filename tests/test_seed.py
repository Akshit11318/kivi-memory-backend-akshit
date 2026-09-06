"""data/seed/observations.json replays deterministically and never smuggles a
content-edit or refused-homophone pair into memory."""

import json
from pathlib import Path
from typing import Iterator

import pytest

from kivi_memory.config import SEED_PATH
from kivi_memory.learner.explicit import replay
from kivi_memory.pipeline.run import run
from kivi_memory.store.db import MemoryStore


@pytest.fixture
def seeded_store(tmp_path: Path) -> Iterator[MemoryStore]:
    with MemoryStore(tmp_path / "kivi.sqlite") as store:
        for entry in json.loads(SEED_PATH.read_text()):
            replay(store, entry)
        yield store


def test_seed_is_not_empty() -> None:
    assert json.loads(SEED_PATH.read_text()) != []


def test_seed_replay_never_learns_content_edit_or_homophone(seeded_store: MemoryStore) -> None:
    canonicals = {m.canonical.lower() for m in seeded_store.list_memories("demo")}
    assert "thursday" not in canonicals
    assert "their" not in canonicals


def test_seed_replay_is_deterministic_row_count(tmp_path: Path) -> None:
    entries = json.loads(SEED_PATH.read_text())
    with MemoryStore(tmp_path / "a.sqlite") as store_a:
        for entry in entries:
            replay(store_a, entry)
        count_a = len(store_a.list_memories())

    with MemoryStore(tmp_path / "b.sqlite") as store_b:
        for entry in entries:
            replay(store_b, entry)
        count_b = len(store_b.list_memories())

    assert count_a == count_b


def test_seed_reproduces_pdf_example(seeded_store: MemoryStore) -> None:
    trace = run(
        seeded_store,
        "demo",
        asr="ask aditya to review the sarvam kiwi service",
        formatted="Ask Aditya to review the Sarvam Kiwi service.",
        profile="exact",
    )
    assert trace.memory_aware == "Ask Aaditya to review the Sarvam Kivi service."
