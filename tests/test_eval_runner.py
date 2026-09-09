"""CSV eval runner: teach replay, hit scoring (TP/FP/FN), and SKIP under --decide ungated."""

from pathlib import Path

from kivi_memory.eval_runner import run_case_row, summarize


def _teaches(*rows: dict) -> dict[str, list[dict]]:
    by_case: dict[str, list[dict]] = {}
    for row in rows:
        by_case.setdefault(row["case_id"], []).append(row)
    return by_case


def _teach_row(case_id: str, **overrides) -> dict:
    base = {
        "case_id": case_id,
        "step": "1",
        "source": "dictionary_add",
        "user_id": "",
        "asr": "",
        "formatted": "",
        "final": "",
        "canonical": "",
        "forms": "",
        "teach_text": "",
    }
    base.update(overrides)
    return base


def _case(**overrides) -> dict:
    base = {
        "id": "t",
        "family": "t",
        "user_id": "",
        "profile": "auto",
        "asr": "",
        "formatted": "",
        "expected_memory_aware": "",
        "expected_hits": "[]",
        "requires_llm": "false",
    }
    base.update(overrides)
    return base


def test_useful_apply_scores_a_true_positive_hit() -> None:
    teaches = _teaches(_teach_row("t", canonical="Aaditya", forms="aditya"))
    case = _case(id="t", formatted="Ask Aditya now.", expected_hits='[{"from": "Aditya", "to": "Aaditya"}]')

    result = run_case_row(case, teaches, decide="ungated")

    assert result.status == "RAN"
    assert result.string_match is True
    assert (result.tp, result.fp, result.fn) == (1, 0, 0)


def test_unexpected_apply_is_a_false_positive_and_string_mismatch() -> None:
    teaches = _teaches(_teach_row("t", canonical="Aaditya", forms="aditya"))
    case = _case(
        id="t",
        formatted="Ask Aditya now.",
        expected_memory_aware="Ask Aditya now.",
        expected_hits="[]",
    )

    result = run_case_row(case, teaches, decide="ungated")

    assert result.tp == 0
    assert result.fp == 1
    assert result.string_match is False


def test_missed_apply_is_a_false_negative() -> None:
    case = _case(
        id="t",
        formatted="Ask Aditya now.",
        expected_memory_aware="Ask Aaditya now.",
        expected_hits='[{"from": "Aditya", "to": "Aaditya"}]',
    )

    result = run_case_row(case, {}, decide="ungated")

    assert result.tp == 0
    assert result.fn == 1
    assert result.string_match is False


def test_requires_llm_row_is_skipped_when_ungated(monkeypatch) -> None:
    monkeypatch.delenv("KIVI_LLM_API_KEY", raising=False)
    case = _case(id="t", requires_llm="true", formatted="Buy kiwi at the store.")

    result = run_case_row(case, {}, decide="ungated")

    assert result.status == "SKIPPED"


def test_off_profile_case_is_a_passthrough() -> None:
    teaches = _teaches(_teach_row("t", canonical="Aaditya", forms="aditya"))
    case = _case(id="t", profile="off", formatted="Ask Aditya now.", expected_memory_aware="Ask Aditya now.")

    result = run_case_row(case, teaches, decide="ungated")

    assert result.status == "RAN"
    assert result.actual_memory_aware == "Ask Aditya now."
    assert result.string_match is True


def test_unknown_profile_column_errors_without_crashing() -> None:
    case = _case(id="t", profile="bogus")
    result = run_case_row(case, {}, decide="ungated")
    assert result.status == "ERROR"


def test_summarize_computes_precision_and_recall_across_rows() -> None:
    teaches = _teaches(_teach_row("hit", canonical="Aaditya", forms="aditya"))
    hit = run_case_row(
        _case(id="hit", formatted="Ask Aditya now.", expected_hits='[{"from": "Aditya", "to": "Aaditya"}]'),
        teaches,
        decide="ungated",
    )
    miss = run_case_row(
        _case(id="miss", formatted="Ask Aditya now.", expected_hits='[{"from": "Aditya", "to": "Aaditya"}]'),
        {},
        decide="ungated",
    )

    summary = summarize([hit, miss])
    totals = summary["totals"]
    assert totals["tp"] == 1
    assert totals["fn"] == 1
    assert totals["precision"] == 1.0
    assert totals["recall"] == 0.5
    assert totals["latency_ms_median"] > 0
    assert totals["latency_ms_max"] >= totals["latency_ms_median"]
    assert totals["rows_with_llm_call"] == 0


def test_dataset_files_load_and_run_without_crashing() -> None:
    """The committed eval/dataset CSVs are real fixtures, not just test doubles."""
    from kivi_memory.eval_runner import run_eval

    results = run_eval(decide="ungated")
    assert len(results) > 0
    assert all(r.status in ("RAN", "SKIPPED", "ERROR") for r in results)
    assert not any(r.status == "ERROR" for r in results)
