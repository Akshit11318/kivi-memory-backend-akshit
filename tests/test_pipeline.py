"""Tokenize, retrieve exact, align, decide, rewrite — end-to-end via pipeline.run."""

from pathlib import Path
from typing import Iterator

import pytest

from kivi_memory.learner.explicit import correction, dictionary_add
from kivi_memory.pipeline.run import run
from kivi_memory.store.db import MemoryStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    with MemoryStore(tmp_path / "kivi.sqlite") as store:
        yield store


def test_pdf_example_exact_profile_after_two_teaches(store: MemoryStore) -> None:
    correction(
        store,
        "demo",
        formatted="Ask Aditya to review the Sarvam Kiwi service.",
        final="Ask Aaditya to review the Sarvam Kivi service.",
        asr="ask aditya to review the sarvam kiwi service",
    )

    trace = run(
        store,
        "demo",
        asr="ask aditya to review the sarvam kiwi service",
        formatted="Ask Aditya to review the Sarvam Kiwi service.",
        profile="exact",
    )
    assert trace.memory_aware == "Ask Aaditya to review the Sarvam Kivi service."
    assert {d.decision for d in trace.decisions if d.token in ("Aditya", "Kiwi")} == {"APPLY"}


def test_off_profile_always_equals_formatted(store: MemoryStore) -> None:
    correction(store, "demo", formatted="Ask Aditya now.", final="Ask Aaditya now.")
    trace = run(
        store, "demo", asr="ask aditya now", formatted="Ask Aditya now.", profile="off"
    )
    assert trace.memory_aware == "Ask Aditya now."
    assert trace.decisions == ()


def test_deliberate_noop_empty_store_abstains(store: MemoryStore) -> None:
    trace = run(
        store,
        "demo",
        asr="let us schedule the call",
        formatted="Let us schedule the call.",
        profile="exact",
    )
    assert trace.memory_aware == "Let us schedule the call."
    assert all(d.decision == "ABSTAIN" for d in trace.decisions)


def test_alignment_required_fixture_gonna_only_touches_aditya(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Aaditya", ["aditya"])
    trace = run(
        store,
        "demo",
        asr="im gonna ask aditya",
        formatted="I'm going to ask Aditya.",
        profile="exact",
    )
    assert trace.memory_aware == "I'm going to ask Aaditya."


def test_word_boundary_no_match_inside_longer_word(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Kivi", ["kivi"])
    trace = run(
        store,
        "demo",
        asr="deploy on kivimaki",
        formatted="Deploy on Kivimaki.",
        profile="exact",
    )
    assert trace.memory_aware == "Deploy on Kivimaki."
    assert all(d.decision == "ABSTAIN" for d in trace.decisions)


def test_already_canonical_token_abstains(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Aaditya", ["aditya"])
    trace = run(store, "demo", asr="", formatted="Ask Aaditya now.", profile="exact")
    decision = next(d for d in trace.decisions if d.token == "Aaditya")
    assert decision.decision == "ABSTAIN"
    assert decision.reason == "already_canonical"


def test_conflicting_canonicals_abstain(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Aaditya", ["aditya"], confidence=0.9)
    store.upsert_memory("demo", "Adithya", ["aditya"], confidence=0.9)
    trace = run(store, "demo", asr="", formatted="Ask Aditya now.", profile="exact")
    decision = next(d for d in trace.decisions if d.token == "Aditya")
    assert decision.decision == "ABSTAIN"
    assert decision.reason == "conflicting_canonicals"
    assert len(decision.memory_ids) == 2


def test_confidence_boundary_075_is_apply(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Aaditya", ["aditya"], confidence=0.75)
    trace = run(store, "demo", asr="", formatted="Ask Aditya now.", profile="exact")
    decision = next(d for d in trace.decisions if d.token == "Aditya")
    assert decision.decision == "APPLY"


def test_below_confidence_boundary_abstains(store: MemoryStore) -> None:
    store.upsert_memory("demo", "Aaditya", ["aditya"], confidence=0.60)
    trace = run(store, "demo", asr="", formatted="Ask Aditya now.", profile="exact")
    decision = next(d for d in trace.decisions if d.token == "Aditya")
    assert decision.decision == "ABSTAIN"
    assert decision.reason == "low_confidence"


def test_possessive_clitic_rewrites_base_and_keeps_suffix(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Kivi", ["kiwi"])
    trace = run(store, "demo", asr="", formatted='Check Kiwi\'s throughput.', profile="exact")
    assert trace.memory_aware == "Check Kivi's throughput."


def test_context_apply_on_work_sentence_abstain_on_grocery(store: MemoryStore) -> None:
    correction(
        store,
        "demo",
        formatted="Ask Aditya to review the Sarvam Kiwi service.",
        final="Ask Aaditya to review the Sarvam Kivi service.",
    )

    work = run(
        store,
        "demo",
        asr="",
        formatted="Please review the Sarvam Kiwi service today.",
        profile="exact",
    )
    kivi_decision = next(d for d in work.decisions if d.token == "Kiwi")
    assert kivi_decision.decision == "APPLY"

    grocery = run(store, "demo", asr="", formatted="Remind me to buy kiwi tomorrow.", profile="exact")
    kiwi_decision = next(d for d in grocery.decisions if d.token == "kiwi")
    assert kiwi_decision.decision == "ABSTAIN"
    assert kiwi_decision.reason == "context_mismatch"


def test_multiple_mentions_one_sentence_all_apply(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Aaditya", ["aditya"])
    trace = run(
        store,
        "demo",
        asr="",
        formatted="Aditya asked Aditya to call Aditya.",
        profile="exact",
    )
    assert trace.memory_aware == "Aaditya asked Aaditya to call Aaditya."


def test_multi_user_isolation(store: MemoryStore) -> None:
    dictionary_add(store, "user_a", "Kivi", ["kiwi"])
    trace = run(store, "user_b", asr="", formatted="Buy some kiwi.", profile="exact")
    assert trace.memory_aware == "Buy some kiwi."


def test_empty_input_no_crash(store: MemoryStore) -> None:
    trace = run(store, "demo", asr="", formatted="", profile="exact")
    assert trace.memory_aware == ""
    assert trace.decisions == ()


def test_unknown_profile_raises(store: MemoryStore) -> None:
    with pytest.raises(NotImplementedError):
        run(store, "demo", asr="", formatted="hello", profile="phonetic")
