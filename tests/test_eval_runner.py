"""Eval runner: setup ordering, classification, and the isolated-DB contract."""

from kivi_memory.eval_runner import _classify, run_case


def _case(**overrides):
    base = {
        "id": "t",
        "family": "t",
        "setup": {},
        "inputs": {"asr": "", "formatted": "", "user_id": "demo_user"},
        "expected": {"expected_profile_results": {}},
    }
    base.update(overrides)
    return base


def test_seeded_row_reinforced_by_a_later_correction_crosses_threshold() -> None:
    """Regression: setup used to apply `observations` before `seeded_memories`,
    so a real correction's 0.85 got stomped back down to the seeded 0.60."""
    case = _case(
        setup={
            "seeded_memories": [
                {"canonical": "Chowdhury", "observed_forms": ["choudhury"], "confidence": 0.6}
            ],
            "observations": [
                {"source": "correction", "formatted": "Choudhury approved.", "final": "Chowdhury approved."}
            ],
        },
        inputs={"asr": "", "formatted": "Choudhury approved the release.", "user_id": "demo_user"},
        expected={
            "expected_profile_results": {
                "exact": {"decision": "APPLY", "memory_aware": "Chowdhury approved the release."}
            }
        },
    )
    outcome = run_case(case, ["exact"])
    exact = outcome.profiles[0]
    assert exact.status == "PASS"
    assert exact.actual_decision == "APPLY"


def test_classify_useful_vs_unnecessary_vs_incorrect_apply() -> None:
    assert _classify("APPLY", "X fixed", None, "X fixed", "X broken") == "useful_apply"
    assert _classify("APPLY", "X same", None, "X same", "X same") == "unnecessary_apply"
    assert _classify("APPLY", "wrong text", None, "right text", "X broken") == "incorrect_apply"


def test_classify_expected_vs_unexpected_abstain() -> None:
    assert _classify("ABSTAIN", None, "ABSTAIN", None, None) == "expected_abstain"
    assert _classify("ABSTAIN", None, "APPLY", None, None) == "unexpected_abstain"


def test_profile_validation_case_is_handled_without_running_pipeline() -> None:
    case = _case(inputs={"asr": "", "formatted": "x", "user_id": "demo_user", "profile": "foo"})
    outcome = run_case(case, ["exact"])
    assert outcome.profiles[0].status == "PASS"
    assert outcome.profiles[0].profile == "foo"


def test_llm_profile_is_skipped_not_failed() -> None:
    case = _case(
        inputs={"asr": "", "formatted": "hello", "user_id": "demo_user"},
        expected={"expected_profile_results": {"llm": {"decision": "APPLY", "memory_aware": "hello"}}},
    )
    outcome = run_case(case, ["llm"])
    assert outcome.profiles[0].status == "SKIPPED"
