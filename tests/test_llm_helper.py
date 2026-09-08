"""LLM sense helper — mocked, never live (`_post_chat_completion` is the seam).

These are the "must-work when a key is present" scenarios from the spec:
fruit vs brand ABSTAIN, staging APPLY with no shared neighbor words, and
Groww/grow ABSTAIN with no teach_text.
"""

from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest

from kivi_memory.learner.explicit import correction, dictionary_add
from kivi_memory.pipeline.run import run
from kivi_memory.store.db import MemoryStore

_PATCH_TARGET = "kivi_memory.decide.llm_helper._post_chat_completion"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[MemoryStore]:
    with MemoryStore(tmp_path / "kivi.sqlite") as store:
        yield store


@pytest.fixture(autouse=True)
def _no_real_key_by_default(monkeypatch):
    monkeypatch.delenv("KIVI_LLM_API_KEY", raising=False)


def test_llm_abstains_on_fruit_sense(store: MemoryStore, monkeypatch) -> None:
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    correction(
        store,
        "demo",
        formatted="Please review the Sarvam Kiwi rollout.",
        final="Please review the Sarvam Kivi rollout.",
    )

    with patch(_PATCH_TARGET, return_value='{"decision": "ABSTAIN", "reason": "fruit_vs_brand"}'):
        trace = run(
            store,
            "demo",
            asr="",
            formatted="Buy kiwi at the store this weekend if the fruit looks good.",
            profile="auto",
        )

    assert trace.memory_aware == "Buy kiwi at the store this weekend if the fruit looks good."
    decision = next(d for d in trace.decisions if d.token == "kiwi")
    assert decision.decision == "ABSTAIN"
    assert decision.helper == "llm"
    assert decision.reason == "fruit_vs_brand"
    assert trace.model_calls == 1


def test_llm_applies_on_staging_sense_with_no_shared_neighbor_words(
    store: MemoryStore, monkeypatch
) -> None:
    """The deleted cue gate needed lexical overlap with the teach sentence.
    "restart", "pod", "staging", "demo" share nothing with "review", "rollout"
    — the LLM still applies because it reasons about sense, not word overlap."""
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    correction(
        store,
        "demo",
        formatted="Please review the Sarvam Kiwi rollout.",
        final="Please review the Sarvam Kivi rollout.",
    )

    with patch(_PATCH_TARGET, return_value='{"decision": "APPLY", "reason": "same_product"}'):
        trace = run(
            store,
            "demo",
            asr="",
            formatted="Restart the Kiwi pod in staging before the client demo tomorrow.",
            profile="auto",
        )

    assert trace.memory_aware == "Restart the Kivi pod in staging before the client demo tomorrow."
    decision = next(d for d in trace.decisions if d.token == "Kiwi")
    assert decision.decision == "APPLY"
    assert decision.canonical == "Kivi"
    assert decision.helper == "llm"


def test_llm_abstains_on_groww_grow_with_no_teach_text(store: MemoryStore, monkeypatch) -> None:
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    dictionary_add(store, "demo", "Groww", ["grow"])

    with patch(_PATCH_TARGET, return_value='{"decision": "ABSTAIN", "reason": "common_word"}'):
        trace = run(
            store, "demo", asr="", formatted="The plants will grow faster in the sun.", profile="auto"
        )

    assert trace.memory_aware == "The plants will grow faster in the sun."
    decision = next(d for d in trace.decisions if d.token == "grow")
    assert decision.decision == "ABSTAIN"
    assert decision.helper == "llm"


def test_no_key_falls_through_to_ungated_apply_no_exception(store: MemoryStore) -> None:
    dictionary_add(store, "demo", "Groww", ["grow"])
    trace = run(store, "demo", asr="", formatted="The plants will grow faster in the sun.", profile="auto")
    decision = next(d for d in trace.decisions if d.token == "grow")
    assert decision.decision == "APPLY"
    assert decision.helper == "ungated"
    assert decision.reason == "ungated"
    assert decision.model is None
    assert trace.model_calls == 0


def test_llm_timeout_falls_through_to_ungated_apply_not_an_exception(
    store: MemoryStore, monkeypatch
) -> None:
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    dictionary_add(store, "demo", "Groww", ["grow"])

    with patch(_PATCH_TARGET, side_effect=TimeoutError("timed out")):
        trace = run(
            store, "demo", asr="", formatted="The plants will grow faster in the sun.", profile="auto"
        )

    decision = next(d for d in trace.decisions if d.token == "grow")
    assert decision.decision == "APPLY"
    assert decision.helper == "ungated"
    # A call was attempted (the key was set) even though it failed.
    assert trace.model_calls == 1


def test_llm_unparseable_response_falls_through_to_ungated_apply(
    store: MemoryStore, monkeypatch
) -> None:
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    dictionary_add(store, "demo", "Groww", ["grow"])

    with patch(_PATCH_TARGET, return_value="not json at all"):
        trace = run(
            store, "demo", asr="", formatted="The plants will grow faster in the sun.", profile="auto"
        )

    decision = next(d for d in trace.decisions if d.token == "grow")
    assert decision.decision == "APPLY"
    assert decision.helper == "ungated"


def test_conflicting_canonicals_abstains_without_ever_calling_the_llm(
    store: MemoryStore, monkeypatch
) -> None:
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    store.upsert_memory("demo", "Aaditya", ["aditya"], confidence=0.9)
    store.upsert_memory("demo", "Adithya", ["aditya"], confidence=0.9)

    with patch(_PATCH_TARGET) as mock_call:
        trace = run(store, "demo", asr="", formatted="Ask Aditya now.", profile="auto")

    mock_call.assert_not_called()
    decision = next(d for d in trace.decisions if d.token == "Aditya")
    assert decision.decision == "ABSTAIN"
    assert decision.reason == "conflicting_canonicals"
    assert decision.helper is None
    assert trace.model_calls == 0


def test_karan_karen_is_a_documented_limitation_not_hidden(store: MemoryStore) -> None:
    """We do not claim the LLM (or the ungated default) solves speaker
    identity: same Metaphone key, no key configured -> it still misfires."""
    dictionary_add(store, "demo", "Karan", ["karan"])
    trace = run(store, "demo", asr="", formatted="Karen joined the call today.", profile="phonetic")
    decision = next(d for d in trace.decisions if d.token == "Karen")
    assert decision.decision == "APPLY"
    assert decision.canonical == "Karan"
