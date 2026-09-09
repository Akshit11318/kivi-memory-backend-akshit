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
        decide="ungated",
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
        decide="ungated",
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
    trace = run(store, "demo", asr="", formatted="Ask Aditya now.", profile="exact", decide="ungated")
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
    trace = run(store, "demo", asr="", formatted='Check Kiwi\'s throughput.', profile="exact", decide="ungated")
    assert trace.memory_aware == "Check Kivi's throughput."


def test_ungated_decide_applies_kiwi_in_grocery_sentence(
    store: MemoryStore,
) -> None:
    """`--decide ungated` is the latency path: APPLY after cheap doors, no
    sense check. Fruit vs brand is `--decide llm`'s job. See test_llm_helper."""
    correction(
        store,
        "demo",
        formatted="Ask Aditya to review the Sarvam Kiwi service.",
        final="Ask Aaditya to review the Sarvam Kivi service.",
    )

    grocery = run(
        store,
        "demo",
        asr="",
        formatted="Remind me to buy kiwi tomorrow.",
        profile="exact",
        decide="ungated",
    )
    kiwi_decision = next(d for d in grocery.decisions if d.token == "kiwi")
    assert kiwi_decision.decision == "APPLY"
    assert kiwi_decision.helper == "ungated"
    assert grocery.memory_aware == "Remind me to buy Kivi tomorrow."
    assert grocery.decide == "ungated"


def test_matched_via_reports_exact_when_surface_already_stored(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Aaditya", ["aditya"])
    trace = run(store, "demo", asr="", formatted="Ask Aditya now.", profile="auto", decide="ungated")
    decision = next(d for d in trace.decisions if d.token == "Aditya")
    assert decision.matched_via == "exact"


def test_matched_via_reports_phonetic_under_auto_when_exact_misses(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Grafana", ["grafana"])
    trace = run(store, "demo", asr="", formatted="Please restart the graffana pod.", profile="auto", decide="ungated")
    decision = next(d for d in trace.decisions if d.token == "graffana")
    assert decision.matched_via == "phonetic"


def test_matched_via_none_when_no_candidates(store: MemoryStore) -> None:
    trace = run(store, "demo", asr="", formatted="Ship it on Friday.", profile="auto")
    decision = next(d for d in trace.decisions if d.token == "Friday")
    assert decision.matched_via is None


def test_sentence_final_word_correction_still_applies_later(store: MemoryStore) -> None:
    correction(
        store,
        "demo",
        formatted="This is a phaneer sandwitch.",
        final="This is a paneer sandwich.",
    )
    trace = run(
        store,
        "demo",
        asr="tis is a phaneer sandhwitch",
        formatted="Tis is a phaneer sandwitch.",
        profile="exact",
        decide="ungated",
    )
    assert trace.memory_aware == "Tis is a paneer sandwich."


def test_multiple_mentions_one_sentence_all_apply(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Aaditya", ["aditya"])
    trace = run(
        store,
        "demo",
        asr="",
        formatted="Aditya asked Aditya to call Aditya.",
        profile="exact",
        decide="ungated",
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


def test_unimplemented_profile_raises(store: MemoryStore) -> None:
    with pytest.raises(NotImplementedError):
        run(store, "demo", asr="", formatted="hello", profile="foo")
