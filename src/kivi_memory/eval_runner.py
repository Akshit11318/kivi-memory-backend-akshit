"""CSV eval runner: teaches.csv + cases.csv, isolated SQLite per case row.

Headline is hits, not "N cases passed": expected_hit is a from -> to pair on
the formatted line asserted by a case; actual_hit is a system APPLY. TP/FP/FN
and precision/recall are computed per profile (the `profile` column on each
case row) and overall.

A case with `requires_llm=true` is SKIPPED, not scored, when no
KIVI_LLM_API_KEY is set — scoring it against ungated behavior would assert
something the run never attempted (see decide/llm_helper.py).
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kivi_memory.config import (
    DEFAULT_USER_ID,
    EVAL_DATASET_DIR,
    EVAL_RESULTS_DIR,
    LLM_API_KEY_ENV,
    PROFILES,
)
from kivi_memory.learner import explicit as explicit_learner
from kivi_memory.pipeline.run import run
from kivi_memory.store.db import MemoryStore

TEACHES_PATH = EVAL_DATASET_DIR / "teaches.csv"
CASES_PATH = EVAL_DATASET_DIR / "cases.csv"


@dataclass
class RowResult:
    id: str
    family: str
    profile: str
    status: str  # RAN | SKIPPED | ERROR
    string_match: bool | None = None
    expected_memory_aware: str | None = None
    actual_memory_aware: str | None = None
    tp: int = 0
    fp: int = 0
    fn: int = 0
    latency_ms: float = 0.0
    model_calls: int = 0
    helper_llm: int = 0
    helper_ungated: int = 0
    note: str = ""


def _split_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split("|") if item.strip()]


def load_teaches(path: Path = TEACHES_PATH) -> dict[str, list[dict[str, Any]]]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_case.setdefault(row["case_id"], []).append(row)
    for rows in by_case.values():
        rows.sort(key=lambda r: int(r["step"] or 0))
    return by_case


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _is_true(raw: str | None) -> bool:
    return str(raw or "").strip().lower() in ("true", "1", "yes")


def _apply_teach(store: MemoryStore, teach_row: dict[str, Any], default_user_id: str) -> None:
    user_id = teach_row.get("user_id") or default_user_id
    source = teach_row["source"]
    if source == "dictionary_add":
        explicit_learner.dictionary_add(
            store,
            user_id,
            teach_row["canonical"],
            _split_list(teach_row.get("forms")),
            teach_row.get("teach_text") or None,
        )
    elif source == "correction":
        explicit_learner.correction(
            store,
            user_id,
            teach_row["formatted"],
            teach_row["final"],
            teach_row.get("asr") or None,
        )
    else:
        raise ValueError(f"unknown teach source {source!r}")


def run_case_row(
    case: dict[str, Any], teaches_by_case: dict[str, list[dict[str, Any]]]
) -> RowResult:
    case_id = case["id"]
    family = case.get("family", "")
    profile = case["profile"]

    requires_llm = _is_true(case.get("requires_llm"))
    has_key = bool(os.environ.get(LLM_API_KEY_ENV))
    if requires_llm and not has_key:
        return RowResult(case_id, family, profile, "SKIPPED", note="requires_llm, no KIVI_LLM_API_KEY")

    if profile not in PROFILES:
        return RowResult(case_id, family, profile, "ERROR", note=f"unknown profile {profile!r}")

    user_id = case.get("user_id") or DEFAULT_USER_ID
    expected_hits = json.loads(case["expected_hits"]) if case.get("expected_hits") else []
    expected_memory_aware = case.get("expected_memory_aware") or None

    with tempfile.TemporaryDirectory(prefix="kivi_eval_") as tmp:
        store = MemoryStore(Path(tmp) / "case.sqlite")
        try:
            for teach_row in teaches_by_case.get(case_id, []):
                _apply_teach(store, teach_row, user_id)

            try:
                trace = run(store, user_id, case.get("asr", ""), case["formatted"], profile)
            except Exception as exc:  # defensive: eval must never hang or crash on one bad row
                return RowResult(case_id, family, profile, "ERROR", note=f"{type(exc).__name__}: {exc}")

            actual = Counter(
                (d.token, d.canonical)
                for d in trace.decisions
                if d.decision == "APPLY" and d.canonical
            )
            expected = Counter((h["from"], h["to"]) for h in expected_hits)
            tp = sum((expected & actual).values())
            fp = sum((actual - expected).values())
            fn = sum((expected - actual).values())
            string_match = expected_memory_aware is None or trace.memory_aware == expected_memory_aware

            return RowResult(
                id=case_id,
                family=family,
                profile=profile,
                status="RAN",
                string_match=string_match,
                expected_memory_aware=expected_memory_aware,
                actual_memory_aware=trace.memory_aware,
                tp=tp,
                fp=fp,
                fn=fn,
                latency_ms=trace.latency_ms,
                model_calls=trace.model_calls,
                helper_llm=sum(1 for d in trace.decisions if d.helper == "llm"),
                helper_ungated=sum(1 for d in trace.decisions if d.helper == "ungated"),
            )
        finally:
            store.close()


def run_eval(
    cases_path: Path = CASES_PATH, teaches_path: Path = TEACHES_PATH
) -> list[RowResult]:
    teaches_by_case = load_teaches(teaches_path)
    return [run_case_row(case, teaches_by_case) for case in load_cases(cases_path)]


def _empty_profile_row() -> dict[str, Any]:
    return {
        "ran": 0,
        "skipped": 0,
        "errors": 0,
        "string_mismatches": 0,
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "latency_ms": 0.0,
        "model_calls": 0,
        "helper_llm": 0,
        "helper_ungated": 0,
    }


def summarize(results: list[RowResult]) -> dict[str, Any]:
    by_profile: dict[str, dict[str, Any]] = {}
    totals = _empty_profile_row()

    for r in results:
        row = by_profile.setdefault(r.profile, _empty_profile_row())
        if r.status == "SKIPPED":
            row["skipped"] += 1
            totals["skipped"] += 1
            continue
        if r.status == "ERROR":
            row["errors"] += 1
            totals["errors"] += 1
            continue

        row["ran"] += 1
        totals["ran"] += 1
        for key in ("tp", "fp", "fn", "latency_ms", "model_calls", "helper_llm", "helper_ungated"):
            value = getattr(r, key)
            row[key] += value
            totals[key] += value
        if r.string_match is False:
            row["string_mismatches"] += 1
            totals["string_mismatches"] += 1

    for row in (*by_profile.values(), totals):
        row["expected_hits"] = row["tp"] + row["fn"]
        row["actual_hits"] = row["tp"] + row["fp"]
        row["precision"] = row["tp"] / (row["tp"] + row["fp"]) if (row["tp"] + row["fp"]) else 1.0
        row["recall"] = row["tp"] / (row["tp"] + row["fn"]) if (row["tp"] + row["fn"]) else 1.0

    return {"by_profile": by_profile, "totals": totals}


def _to_json(results: list[RowResult]) -> dict[str, Any]:
    return {
        "rows": [
            {
                "id": r.id,
                "family": r.family,
                "profile": r.profile,
                "status": r.status,
                "string_match": r.string_match,
                "expected_memory_aware": r.expected_memory_aware,
                "actual_memory_aware": r.actual_memory_aware,
                "tp": r.tp,
                "fp": r.fp,
                "fn": r.fn,
                "latency_ms": r.latency_ms,
                "model_calls": r.model_calls,
                "helper_llm": r.helper_llm,
                "helper_ungated": r.helper_ungated,
                "note": r.note,
            }
            for r in results
        ],
        "summary": summarize(results),
    }


def _fmt_row(name: str, row: dict[str, Any]) -> str:
    return (
        f"| {name} | {row['expected_hits']} | {row['actual_hits']} | {row['tp']} | {row['fp']} | "
        f"{row['fn']} | {row['precision']:.2f} | {row['recall']:.2f} | {row['ran']} | {row['skipped']} | "
        f"{row['errors']} | {row['string_mismatches']} | {row['model_calls']} | {row['helper_llm']} | "
        f"{row['helper_ungated']} | {row['latency_ms']:.2f} |"
    )


def _to_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    totals = summary["totals"]
    lines = ["# Kivi eval results", ""]
    lines.append(
        f"**{totals['expected_hits']} expected hits, {totals['actual_hits']} actual hits — "
        f"TP {totals['tp']}, FP {totals['fp']}, FN {totals['fn']}, "
        f"precision {totals['precision']:.2f}, recall {totals['recall']:.2f}.**"
    )
    lines.append("")
    lines.append(
        f"{totals['ran']} rows ran, {totals['skipped']} skipped (requires_llm, no key), "
        f"{totals['errors']} errored, {totals['string_mismatches']} string mismatch(es)."
    )
    lines.append("")
    lines.append("## By profile")
    lines.append("")
    header = (
        "| profile | expected_hits | actual_hits | TP | FP | FN | precision | recall | ran | "
        "skipped | errors | string_mismatches | model_calls | helper_llm | helper_ungated | latency_ms |"
    )
    lines.append(header)
    lines.append("|" + " --- |" * (header.count("|") - 1))
    for profile, row in summary["by_profile"].items():
        lines.append(_fmt_row(profile, row))
    lines.append(_fmt_row("**total**", totals))
    lines.append("")

    failures = [
        r
        for r in report["rows"]
        if r["status"] == "ERROR" or r["string_match"] is False or r["fp"] > 0
    ]
    if failures:
        lines.append("## Failures")
        lines.append("")
        lines.append("| id | profile | status | issue |")
        lines.append("| --- | --- | --- | --- |")
        for r in failures:
            if r["status"] == "ERROR":
                issue = r["note"]
            elif r["string_match"] is False:
                issue = (
                    f"text mismatch: expected {r['expected_memory_aware']!r}, "
                    f"got {r['actual_memory_aware']!r}"
                )
            else:
                issue = f"{r['fp']} unexpected APPLY(s)"
            lines.append(f"| {r['id']} | {r['profile']} | {r['status']} | {issue} |")
        lines.append("")

    return "\n".join(lines)


def write_report(results: list[RowResult], results_dir: Path = EVAL_RESULTS_DIR) -> dict[str, Any]:
    results_dir.mkdir(parents=True, exist_ok=True)
    report = _to_json(results)
    (results_dir / "latest.json").write_text(json.dumps(report, indent=2) + "\n")
    (results_dir / "latest.md").write_text(_to_markdown(report) + "\n")
    return report
