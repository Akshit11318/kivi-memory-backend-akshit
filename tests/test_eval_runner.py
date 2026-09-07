"""Eval runner: setup ordering, classification, and the isolated-DB contract."""

from kivi_memory.eval_runner import _assertion_coverage, _classify, run_case


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


def _kiwi_cue_case(**expected_exact):
    """Memory taught from a work sentence; utterance is the grocery line. The
    right answer is ABSTAIN *because of the cue gate*, not because retrieval
    came up empty."""
    return _case(
        setup={
            "observations": [
                {
                    "source": "correction",
                    "formatted": "Review the Sarvam Kiwi service.",
                    "final": "Review the Sarvam Kivi service.",
                }
            ]
        },
        inputs={
            "asr": "buy kiwi and bananas tomorrow",
            "formatted": "Buy kiwi and bananas tomorrow.",
            "user_id": "demo_user",
        },
        expected={
            "expected_profile_results": {
                "exact": {
                    "decision": "ABSTAIN",
                    "memory_aware": "Buy kiwi and bananas tomorrow.",
                    **expected_exact,
                }
            }
        },
    )


def test_reason_assertion_distinguishes_cue_gate_from_empty_retrieval() -> None:
    """Decision + text alone cannot tell these apart, so the suite could stay
    green with the cue gate deleted. Asserting the reason closes that."""
    right = run_case(_kiwi_cue_case(reasons=["context_mismatch"]), ["exact"]).profiles[0]
    assert right.status == "PASS"
    assert right.actual_reasons == ("context_mismatch",)

    wrong = run_case(_kiwi_cue_case(reasons=["no_memory"]), ["exact"]).profiles[0]
    assert wrong.status == "FAIL"
    assert wrong.actual_decision == "ABSTAIN"  # decision still matched
    assert any("reasons expected" in f for f in wrong.assertion_failures)


def test_affected_tokens_assertion_catches_the_wrong_token_being_rewritten() -> None:
    case = _case(
        setup={"observations": [{"source": "dictionary_add", "canonical": "Groww", "forms": ["grow"]}]},
        inputs={
            "asr": "i moved my sip to grow",
            "formatted": "I moved my SIP to grow.",
            "user_id": "demo_user",
        },
        expected={
            "expected_profile_results": {
                "exact": {
                    "decision": "APPLY",
                    "memory_aware": "I moved my SIP to Groww.",
                    "affected_tokens": [{"from": "grow", "to": "Groww"}],
                }
            }
        },
    )
    outcome = run_case(case, ["exact"])
    assert outcome.profiles[0].status == "PASS"
    assert outcome.profiles[0].actual_affected_tokens == ({"from": "grow", "to": "Groww"},)


def test_memory_row_count_assertion_fails_a_learner_gate_case_that_taught_something() -> None:
    """`Friday -> Thursday` must write nothing. Asserting only the ABSTAIN would
    pass even if the learner had stored a bogus row."""
    setup = {
        "observations": [
            {"source": "correction", "formatted": "Ship it on Friday.", "final": "Ship it on Thursday."}
        ]
    }
    inputs = {"asr": "ship it on friday", "formatted": "Ship it on Friday.", "user_id": "demo_user"}
    profiles = {"exact": {"decision": "ABSTAIN", "memory_aware": "Ship it on Friday."}}

    ok = run_case(
        _case(setup=setup, inputs=inputs,
              expected={"memory_row_count": 0, "expected_profile_results": profiles}),
        ["exact"],
    )
    assert ok.setup_ok is True
    assert ok.profiles[0].status == "PASS"

    bad = run_case(
        _case(setup=setup, inputs=inputs,
              expected={"memory_row_count": 1, "expected_profile_results": profiles}),
        ["exact"],
    )
    assert bad.setup_ok is False
    assert bad.profiles[0].status == "FAIL"
    assert any("memory_row_count" in f for f in bad.profiles[0].assertion_failures)


def test_off_control_is_available_even_when_off_was_not_requested() -> None:
    """`unnecessary_apply` is defined against the `off` output, so the control
    has to be computed regardless of what the caller asked for."""
    case = _case(
        setup={"observations": [{"source": "dictionary_add", "canonical": "Groww", "forms": ["grow"]}]},
        inputs={"asr": "sip to grow", "formatted": "SIP to grow.", "user_id": "demo_user"},
        expected={
            "expected_profile_results": {
                "exact": {"decision": "APPLY", "memory_aware": "SIP to Groww."}
            }
        },
    )
    outcome = run_case(case, ["exact"])
    assert outcome.profiles[0].status == "PASS"
    assert outcome.profiles[0].classification == "useful_apply"


def test_assertion_coverage_names_cases_that_only_check_decision_and_text() -> None:
    weak = run_case(_kiwi_cue_case(), ["exact"])
    strong = run_case(_kiwi_cue_case(reasons=["context_mismatch"]), ["exact"])
    strong.id = "strong"
    coverage = _assertion_coverage([weak, strong])
    assert coverage["asserting_reasons"] == 1
    assert coverage["cases_asserting_decision_and_text_only"] == ["t"]

