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

    with patch(
        _PATCH_TARGET,
        return_value=(
            '{"occurrences": [{"occurrence": 1, "score": 5, "reason": "fruit_vs_brand"}]}',
            {"prompt_tokens": 120, "completion_tokens": 18},
        ),
    ):
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
    assert decision.llm_score == 5
    assert trace.model_calls == 1
    assert trace.prompt_tokens == 120
    assert trace.completion_tokens == 18


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

    with patch(
        _PATCH_TARGET,
        return_value=(
            '{"occurrences": [{"occurrence": 1, "score": 95, "reason": "same_product"}]}',
            {"prompt_tokens": 130, "completion_tokens": 15},
        ),
    ):
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
    assert decision.llm_score == 95


def test_llm_abstains_on_groww_grow_with_no_teach_text(store: MemoryStore, monkeypatch) -> None:
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    dictionary_add(store, "demo", "Groww", ["grow"])

    with patch(
        _PATCH_TARGET,
        return_value=(
            '{"occurrences": [{"occurrence": 1, "score": 5, "reason": "common_word"}]}',
            {"prompt_tokens": 90, "completion_tokens": 12},
        ),
    ):
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

    with patch(_PATCH_TARGET, return_value=("not json at all", {})):
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


def test_same_word_twice_different_sense_in_one_sentence_gets_independent_verdicts(
    store: MemoryStore, monkeypatch
) -> None:
    """"move the stocks and sips from grow as the profits didnt grow last fy" --
    the first "grow" is the brand (APPLY), the second is the ordinary verb
    (ABSTAIN). Both occurrences are scored in ONE batched call (model_calls
    == 1, not 2); the [[#1: ...]]/[[#2: ...]] numbering is what lets the
    response tell them apart. Confirms the fix for the exact bug found
    manually: before numbered marking, a single-occurrence prompt sent
    twice was identical both times and got the identical verdict both
    times."""
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    dictionary_add(
        store, "demo", "Groww", ["grow"], context="He opened a mutual fund SIP on Groww last month."
    )

    def fake_call(base_url, api_key, model, prompt):
        assert "[[#1: grow]]" in prompt and "[[#2: grow]]" in prompt
        content = (
            '{"occurrences": ['
            '{"occurrence": 1, "score": 95, "reason": "brand: moved funds from it"}, '
            '{"occurrence": 2, "score": 5, "reason": "ordinary verb: profits growing"}'
            "]}"
        )
        return content, {"prompt_tokens": 150, "completion_tokens": 30}

    with patch(_PATCH_TARGET, side_effect=fake_call) as mock_call:
        trace = run(
            store,
            "demo",
            asr="",
            formatted="move the stocks and sips from grow as the profits didnt grow last fy",
            profile="auto",
        )

    assert mock_call.call_count == 1
    assert trace.memory_aware == (
        "move the stocks and sips from Groww as the profits didnt grow last fy"
    )
    grow_decisions = [d for d in trace.decisions if d.token == "grow"]
    assert len(grow_decisions) == 2
    assert grow_decisions[0].decision == "APPLY"
    assert grow_decisions[1].decision == "ABSTAIN"
    assert trace.model_calls == 1  # one HTTP call scored both occurrences
    assert trace.prompt_tokens == 150  # attributed once, not double-counted per occurrence
    assert trace.completion_tokens == 30
    assert grow_decisions[0].prompt_tokens == 150
    assert grow_decisions[1].prompt_tokens is None


def test_batch_falls_through_to_ungated_on_occurrence_count_mismatch(
    store: MemoryStore, monkeypatch
) -> None:
    """The model must return exactly one scored item per marked occurrence.
    Returning the wrong count is treated like any other malformed response
    -- ungated APPLY for every occurrence in the batch, not a crash."""
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    dictionary_add(store, "demo", "Groww", ["grow"])

    with patch(
        _PATCH_TARGET,
        return_value=(
            '{"occurrences": [{"occurrence": 1, "score": 5, "reason": "only one"}]}',
            {"prompt_tokens": 80, "completion_tokens": 10},
        ),
    ):
        trace = run(
            store,
            "demo",
            asr="",
            formatted="Watch it grow, then let it grow some more.",
            profile="auto",
        )

    grow_decisions = [d for d in trace.decisions if d.token == "grow"]
    assert len(grow_decisions) == 2
    assert all(d.decision == "APPLY" and d.helper == "ungated" for d in grow_decisions)
    assert trace.model_calls == 1


def test_score_is_blended_with_memory_confidence_not_used_alone(store: MemoryStore, monkeypatch) -> None:
    """A mid-range score (60) is enough to APPLY for a confidence-1.0
    dictionary_add (combined = 1.0 * 0.60 = 0.60 >= 0.5) but not enough for a
    confidence-0.85 first correction (combined = 0.85 * 0.60 = 0.51 -- still
    over by a hair, so use a lower score to show the abstain side)."""
    monkeypatch.setenv("KIVI_LLM_API_KEY", "test-key")
    dictionary_add(store, "demo", "Groww", ["grow"])

    with patch(
        _PATCH_TARGET,
        return_value=(
            '{"occurrences": [{"occurrence": 1, "score": 60, "reason": "leaning brand"}]}',
            {"prompt_tokens": 70, "completion_tokens": 10},
        ),
    ):
        trace = run(store, "demo", asr="", formatted="I moved my SIP to grow.", profile="auto")
    decision = next(d for d in trace.decisions if d.token == "grow")
    assert decision.decision == "APPLY"  # 1.0 * 0.60 = 0.60 >= 0.5
    assert decision.llm_score == 60

    correction(store, "demo", formatted="Ask Aditya now.", final="Ask Aaditya now.")
    with patch(
        _PATCH_TARGET,
        return_value=(
            '{"occurrences": [{"occurrence": 1, "score": 55, "reason": "leaning apply, low confidence"}]}',
            {"prompt_tokens": 70, "completion_tokens": 10},
        ),
    ):
        trace = run(store, "demo", asr="", formatted="Tell Aditya later.", profile="auto")
    decision = next(d for d in trace.decisions if d.token == "Aditya")
    assert decision.decision == "ABSTAIN"  # 0.85 * 0.55 = 0.4675 < 0.5
    assert decision.llm_score == 55


def test_karan_karen_is_a_documented_limitation_not_hidden(store: MemoryStore) -> None:
    """We do not claim the LLM (or the ungated default) solves speaker
    identity: same Metaphone key, no key configured -> it still misfires."""
    dictionary_add(store, "demo", "Karan", ["karan"])
    trace = run(store, "demo", asr="", formatted="Karen joined the call today.", profile="phonetic")
    decision = next(d for d in trace.decisions if d.token == "Karen")
    assert decision.decision == "APPLY"
    assert decision.canonical == "Karan"
