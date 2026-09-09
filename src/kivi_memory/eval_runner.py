"""CSV eval runner: teaches.csv + cases.csv, isolated SQLite per case row.

Headline is hits, not "N cases passed": expected_hit is a from -> to pair on
the formatted line asserted by a case; actual_hit is a system APPLY. TP/FP/FN
and precision/recall are computed per profile (the `profile` column on each
case row) and overall.

A case with `requires_llm=true` is SKIPPED, not scored, when `--decide
ungated` is used — scoring it against ungated APPLY would assert a sense
check the run never attempted (see decide/llm_helper.py). `--decide llm`
(the default) requires KIVI_LLM_API_KEY and KIVI_LLM_MODEL.
"""

from __future__ import annotations

import csv
import json
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

from kivi_memory.config import (
    DECIDE_MODES,
    DEFAULT_DECIDE,
    DEFAULT_USER_ID,
    EVAL_DATASET_DIR,
    EVAL_RESULTS_DIR,
    PROFILES,
    llm_credentials,
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
    llm_latency_ms: float = 0.0
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
    case: dict[str, Any],
    teaches_by_case: dict[str, list[dict[str, Any]]],
    decide: str = DEFAULT_DECIDE,
) -> RowResult:
    case_id = case["id"]
    family = case.get("family", "")
    profile = case["profile"]

    if decide not in DECIDE_MODES:
        return RowResult(case_id, family, profile, "ERROR", note=f"unknown decide {decide!r}")

    requires_llm = _is_true(case.get("requires_llm"))
    if decide == "ungated" and requires_llm:
        return RowResult(
            case_id, family, profile, "SKIPPED", note="requires_llm, --decide ungated"
        )
    if decide == "llm" and llm_credentials() is None:
        return RowResult(
            case_id,
            family,
            profile,
            "ERROR",
            note="missing KIVI_LLM_API_KEY or KIVI_LLM_MODEL",
        )

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
                trace = run(
                    store,
                    user_id,
                    case.get("asr", ""),
                    case["formatted"],
                    profile,
                    decide=decide,
                )
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
            llm_ms = max((d.llm_latency_ms or 0.0) for d in trace.decisions) if trace.decisions else 0.0

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
                llm_latency_ms=llm_ms,
                model_calls=trace.model_calls,
                helper_llm=sum(1 for d in trace.decisions if d.helper == "llm"),
                helper_ungated=sum(1 for d in trace.decisions if d.helper == "ungated"),
            )
        finally:
            store.close()


def run_eval(
    cases_path: Path = CASES_PATH,
    teaches_path: Path = TEACHES_PATH,
    decide: str = DEFAULT_DECIDE,
) -> list[RowResult]:
    teaches_by_case = load_teaches(teaches_path)
    return [run_case_row(case, teaches_by_case, decide=decide) for case in load_cases(cases_path)]


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
        "llm_latency_ms": 0.0,
        "model_calls": 0,
        "helper_llm": 0,
        "helper_ungated": 0,
    }


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    f, c = int(k), min(int(k) + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (k - f) * (ordered[c] - ordered[f])


def _timing_block(latencies: list[float], llm_latencies: list[float]) -> dict[str, float]:
    llm_only = [ms for ms in llm_latencies if ms > 0]
    return {
        "latency_ms_mean": mean(latencies) if latencies else 0.0,
        "latency_ms_median": median(latencies) if latencies else 0.0,
        "latency_ms_p95": _percentile(latencies, 0.95),
        "latency_ms_max": max(latencies) if latencies else 0.0,
        "llm_latency_ms_mean": mean(llm_only) if llm_only else 0.0,
        "llm_latency_ms_max": max(llm_only) if llm_only else 0.0,
        "rows_with_llm_call": float(len(llm_only)),
    }


def summarize(results: list[RowResult]) -> dict[str, Any]:
    by_profile: dict[str, dict[str, Any]] = {}
    totals = _empty_profile_row()
    latencies_by_profile: dict[str, list[float]] = {}
    llm_by_profile: dict[str, list[float]] = {}
    all_latencies: list[float] = []
    all_llm: list[float] = []

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
        for key in (
            "tp",
            "fp",
            "fn",
            "latency_ms",
            "llm_latency_ms",
            "model_calls",
            "helper_llm",
            "helper_ungated",
        ):
            value = getattr(r, key)
            row[key] += value
            totals[key] += value
        if r.string_match is False:
            row["string_mismatches"] += 1
            totals["string_mismatches"] += 1
        latencies_by_profile.setdefault(r.profile, []).append(r.latency_ms)
        llm_by_profile.setdefault(r.profile, []).append(r.llm_latency_ms)
        all_latencies.append(r.latency_ms)
        all_llm.append(r.llm_latency_ms)

    for row in (*by_profile.values(), totals):
        row["expected_hits"] = row["tp"] + row["fn"]
        row["actual_hits"] = row["tp"] + row["fp"]
        row["precision"] = row["tp"] / (row["tp"] + row["fp"]) if (row["tp"] + row["fp"]) else 1.0
        row["recall"] = row["tp"] / (row["tp"] + row["fn"]) if (row["tp"] + row["fn"]) else 1.0

    for profile, row in by_profile.items():
        row.update(_timing_block(latencies_by_profile.get(profile, []), llm_by_profile.get(profile, [])))
    totals.update(_timing_block(all_latencies, all_llm))

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
                "llm_latency_ms": r.llm_latency_ms,
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
        f"{totals['ran']} rows ran, {totals['skipped']} skipped "
        f"(requires_llm under --decide ungated), "
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
    lines.append("## Time")
    lines.append("")
    lines.append("| | ms |")
    lines.append("| --- | ---: |")
    lines.append(f"| typical row (median) | {totals['latency_ms_median']:.1f} |")
    lines.append(f"| average row | {totals['latency_ms_mean']:.1f} |")
    lines.append(f"| p95 row | {totals['latency_ms_p95']:.1f} |")
    lines.append(f"| slowest row | {totals['latency_ms_max']:.1f} |")
    lines.append(f"| sum of pipeline times | {totals['latency_ms']:.1f} |")
    if totals.get("rows_with_llm_call"):
        lines.append(f"| typical model HTTP call | {totals['llm_latency_ms_mean']:.1f} |")
        lines.append(f"| slowest model HTTP call | {totals['llm_latency_ms_max']:.1f} |")
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
