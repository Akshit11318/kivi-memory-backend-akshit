"""Explicit learner — dictionary_add, correction gate, cues, confidence."""

from pathlib import Path
from typing import Iterator

import pytest

from kivi_memory.learner.align import (
    diff_words,
    is_grapheme_similar,
    passes_grapheme_gate,
)
from kivi_memory.learner.explicit import correction, dictionary_add
from kivi_memory.store.db import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    with MemoryStore(tmp_path / "kivi.sqlite") as store:
        yield store


def test_dictionary_add_confidence_is_1(store: MemoryStore) -> None:
    memory = dictionary_add(store, "demo", "Kivi", ["kiwi", "Kiwi"])
    assert memory.confidence == 1.0
    assert set(memory.forms) >= {"kivi", "kiwi"}
    assert memory.teach_text is None


def test_dictionary_add_context_is_stored_as_teach_text_only(store: MemoryStore) -> None:
    memory = dictionary_add(store, "demo", "Groww", ["grow"], context="I moved my SIP to Groww.")
    assert memory.teach_text == "I moved my SIP to Groww."


def test_repeated_dictionary_add_same_canonical_merges_forms(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Kivi", ["kiwi"])
    merged = dictionary_add(store, "demo", "Kivi", ["Kivvy"])

    assert len(store.list_memories()) == 1
    assert set(merged.forms) >= {"kivi", "kiwi", "kivvy"}


def test_correction_learns_pdf_example_both_words(store: MemoryStore) -> None:
    outcomes = correction(
        store,
        "demo",
        formatted="Ask Aditya to review the Sarvam Kiwi service.",
        final="Ask Aaditya to review the Sarvam Kivi service.",
        asr="ask aditya to review the sarvam kiwi service",
    )

    learned = {o.final_word: o for o in outcomes if o.learned}
    assert set(learned) == {"Aaditya", "Kivi"}
    assert learned["Aaditya"].memory.confidence == 0.85
    assert learned["Kivi"].memory.confidence == 0.85


def test_correction_stores_final_sentence_as_teach_text(store: MemoryStore) -> None:
    correction(
        store,
        "demo",
        formatted="Ask Aditya to review the Sarvam Kiwi service.",
        final="Ask Aaditya to review the Sarvam Kivi service.",
    )
    kivi = store.get_memory_by_canonical("demo", "Kivi")
    assert kivi is not None
    assert kivi.teach_text == "Ask Aaditya to review the Sarvam Kivi service."


def test_correction_rejects_content_edit_friday_thursday(store: MemoryStore) -> None:
    outcomes = correction(
        store, "demo", formatted="Let's meet on Friday.", final="Let's meet on Thursday."
    )
    assert all(not o.learned for o in outcomes)
    assert store.list_memories() == []


def test_correction_rejects_refused_homophone_there_their(store: MemoryStore) -> None:
    outcomes = correction(
        store, "demo", formatted="I left it over there.", final="I left it over their."
    )
    assert all(not o.learned for o in outcomes)
    assert any(o.reason == "refused_homophone" for o in outcomes)
    assert store.list_memories() == []


def test_correction_rejects_case_only_change(store: MemoryStore) -> None:
    outcomes = correction(store, "demo", formatted="kivi is great.", final="Kivi is great.")
    assert all(not o.learned for o in outcomes)


def test_second_correction_bumps_confidence_by_005_capped(store: MemoryStore) -> None:
    correction(store, "demo", formatted="Ask Aditya now.", final="Ask Aaditya now.")
    outcomes = correction(store, "demo", formatted="Tell Aditya later.", final="Tell Aaditya later.")
    learned = next(o for o in outcomes if o.learned)
    assert learned.memory.confidence == pytest.approx(0.90)


def test_first_correction_overrides_seeded_below_threshold_to_085(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Aaditya", ["aditya"], confidence=0.60)
    outcomes = correction(store, "demo", formatted="Ask Aditya now.", final="Ask Aaditya now.")
    learned = next(o for o in outcomes if o.learned)
    assert learned.memory.confidence == 0.85


def test_dictionary_add_confidence_not_lowered_by_later_correction(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Kivi", ["kiwi"])
    outcomes = correction(store, "demo", formatted="Use the Kiwi service.", final="Use the Kivi service.")
    learned = next(o for o in outcomes if o.learned)
    assert learned.memory.confidence == 1.0


def test_correction_strips_trailing_punctuation_from_sentence_final_word(store: MemoryStore) -> None:
    outcomes = correction(
        store,
        "demo",
        formatted="This is a phaneer sandwitch.",
        final="This is a paneer sandwich.",
    )
    learned = {o.final_word.rstrip("."): o for o in outcomes if o.learned}
    sandwich = learned["sandwich"].memory
    assert sandwich is not None
    assert sandwich.canonical == "sandwich"
    assert set(sandwich.forms) == {"sandwich", "sandwitch"}


def test_grapheme_gate_there_their_scores_higher_than_kiwi_kivi_but_still_refused() -> None:
    assert is_grapheme_similar("there", "their") is True
    assert is_grapheme_similar("kiwi", "kivi") is True
    passed, reason = passes_grapheme_gate("there", "their")
    assert passed is False
    assert reason == "refused_homophone"


def test_diff_words_finds_only_equal_length_replace_spans() -> None:
    corrections = diff_words(
        "Ask Aditya to review the Sarvam Kiwi service.",
        "Ask Aaditya to review the Sarvam Kivi service.",
    )
    pairs = {(c.formatted_word, c.final_word) for c in corrections}
    assert pairs == {("Aditya", "Aaditya"), ("Kiwi", "Kivi")}
