"""Eval runner: loads cases, isolates DB, runs profiles, writes results.

Same fixtures x profiles, isolated SQLite per case, compared against
`off` as the control. No hidden benchmark: every case here is a
committed file.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kivi_memory.config import DEFAULT_USER_ID, EVAL_CASES_DIR, EVAL_RESULTS_DIR, PROFILES
from kivi_memory.learner.explicit import replay
from kivi_memory.pipeline.run import run
from kivi_memory.store.db import MemoryStore
from kivi_memory.trace.format import overall_decision

_NOT_A_CASE_FILE = {"manifest.json"}


@dataclass
class ProfileOutcome:
    profile: str
    status: str  # PASS | FAIL | SKIPPED | ERROR
    expected_decision: str | None
    actual_decision: str | None
    expected_memory_aware: str | None
    actual_memory_aware: str | None
    classification: str | None
    reason: str
    latency_ms: float = 0.0
    model_calls: int = 0
    memory_ids_used: tuple[int, ...] = ()
    # Why-level assertions. A case that only checks decision + text cannot tell
    # "abstained because the cue gate fired" from "abstained because retrieval
    # found nothing" — delete the cue gate and such a case still passes. These
    # are optional per case; `assertion_failures` records the ones that ran and
    # disagreed, and every entry here forces status FAIL.
    expected_reasons: tuple[str, ...] | None = None
    actual_reasons: tuple[str, ...] = ()
    expected_affected_tokens: tuple[dict[str, str], ...] | None = None
    actual_affected_tokens: tuple[dict[str, str], ...] = ()
    assertion_failures: tuple[str, ...] = ()


@dataclass
class CaseOutcome:
    id: str
    family: str
    memory_row_count: int
    profiles: list[ProfileOutcome] = field(default_factory=list)
    expected_memory_row_count: int | None = None
    setup_ok: bool = True


def load_cases(cases_dir: Path = EVAL_CASES_DIR) -> list[dict[str, Any]]:
    cases = []
    for path in sorted(cases_dir.glob("case_*.json")):
        if path.name in _NOT_A_CASE_FILE:
            continue
        cases.append(json.loads(path.read_text()))
    return cases


def _apply_setup(store: MemoryStore, case: dict[str, Any], user_id: str) -> None:
    """Seeded rows establish initial state first, so a later reinforcing
    correction observation can build on top of them (threshold-crossing
    fixtures seed a weak row, then replay a real correction over it)."""
    setup = case.get("setup", {})

    for entry in setup.get("seeded_memories", []):
        forms = {str(f).lower() for f in entry.get("observed_forms", [])}
        forms.add(str(entry["canonical"]).lower())
        store.upsert_memory(
            user_id=entry.get("user_id", user_id),
            canonical=entry["canonical"],
            forms=forms,
            confidence=float(entry["confidence"]),
            context_cues=tuple(entry.get("context_cues", ())),
        )

    for entry in setup.get("observations", []):
        if entry.get("source") not in ("dictionary_add", "correction"):
            # e.g. "raw_pair": documents an ASR+formatted pair the user never
            # asserted a correction on. The fixture's point is that this must
            # teach nothing, so skipping it here is the correct behavior, not
            # a workaround. `replay()` stays strict for the real seed file.
            continue
        replay(store, {**entry, "user_id": entry.get("user_id", user_id)})


def _run_one_profile(store: MemoryStore, user_id: str, inputs: dict[str, Any], profile: str):
    try:
        trace = run(store, user_id, inputs.get("asr", ""), inputs.get("formatted", ""), profile)
        return trace, "RAN", "ok"
    except NotImplementedError as exc:
        return None, "SKIPPED", str(exc)
    except Exception as exc:  # defensive: eval must never hang or crash on one bad case
        return None, "ERROR", f"{type(exc).__name__}: {exc}"


def _decisive_reasons(trace) -> tuple[str, ...]:
    """The reasons for tokens that actually had a candidate memory.

    Every token with no candidate reports `no_memory`, so the raw reason set of a
    six-word sentence is mostly noise. The decisive tokens are the ones where
    retrieval returned something and `decide` had a real choice to make; those
    reasons are what a case should assert. Falls back to `("no_memory",)` when
    retrieval found nothing anywhere, which is itself the assertable fact for an
    out-of-scope case.
    """
    decisive = sorted({d.reason for d in trace.decisions if d.memory_ids})
    return tuple(decisive) if decisive else ("no_memory",)


def _applied_tokens(trace) -> tuple[dict[str, str], ...]:
    return tuple(
        {"from": d.token, "to": d.canonical}
        for d in trace.decisions
        if d.decision == "APPLY" and d.canonical
    )


def _normalize_tokens(raw) -> tuple[dict[str, str], ...] | None:
    if raw is None:
        return None
    return tuple({"from": str(t["from"]), "to": str(t["to"])} for t in raw)


def _classify(
    actual_decision: str,
    actual_memory_aware: str | None,
    expected_decision: str | None,
    expected_memory_aware: str | None,
    off_memory_aware: str | None,
) -> str:
    if actual_decision == "APPLY":
        if expected_memory_aware is not None and actual_memory_aware == expected_memory_aware:
            if off_memory_aware is not None and expected_memory_aware == off_memory_aware:
                return "unnecessary_apply"
            return "useful_apply"
        return "incorrect_apply"
    return "expected_abstain" if expected_decision == "ABSTAIN" else "unexpected_abstain"


def _evaluate_profile_validation_case(case: dict[str, Any], requested_profiles: list[str]) -> CaseOutcome:
    bad_profile = case["inputs"]["profile"]
    rejected = bad_profile not in PROFILES
    outcome = ProfileOutcome(
        profile=bad_profile,
        status="PASS" if rejected else "FAIL",
        expected_decision="ERROR",
        actual_decision="ERROR" if rejected else "APPLY_OR_ABSTAIN",
        expected_memory_aware=None,
        actual_memory_aware=None,
        classification=None,
        reason=f"{bad_profile!r} not in {PROFILES}" if rejected else f"{bad_profile!r} was wrongly accepted",
    )
    return CaseOutcome(id=case["id"], family=case.get("family", ""), memory_row_count=0, profiles=[outcome])


def run_case(case: dict[str, Any], requested_profiles: list[str]) -> CaseOutcome:
    inputs = case.get("inputs", {})
    if "profile" in inputs:
        return _evaluate_profile_validation_case(case, requested_profiles)

    user_id = inputs.get("user_id", DEFAULT_USER_ID)
    expected = case.get("expected", {})
    expected_by_profile = expected.get("expected_profile_results", {})

    with tempfile.TemporaryDirectory(prefix="kivi_eval_") as tmp:
        store = MemoryStore(Path(tmp) / "case.sqlite")
        try:
            _apply_setup(store, case, user_id)
            row_count = len(store.list_memories(user_id))

            # Learner-gate cases ("this must teach nothing") are only real if the
            # store is inspected. Without this, deleting the grapheme gate leaves
            # them green.
            expected_rows = expected.get("memory_row_count")
            setup_ok = expected_rows is None or int(expected_rows) == row_count
            setup_failure = (
                ()
                if setup_ok
                else (f"memory_row_count expected {expected_rows}, store has {row_count}",)
            )

            traces: dict[str, Any] = {}
            # The `off` control is what "did memory change anything?" is measured
            # against, so it must exist even when the caller did not ask for it.
            control_trace, control_status, _ = _run_one_profile(store, user_id, inputs, "off")
            if control_status == "RAN":
                traces["off"] = control_trace

            outcomes: list[ProfileOutcome] = []
            for profile in requested_profiles:
                trace, status, reason = _run_one_profile(store, user_id, inputs, profile)
                traces[profile] = trace
                expected_profile = expected_by_profile.get(profile, {})
                expected_decision = expected_profile.get("decision")
                expected_memory_aware = expected_profile.get("memory_aware")

                # Why-assertions are per-profile only, never inherited from the
                # case level. `off` rewrites nothing and `exact`/`phonetic`
                # legitimately abstain for different reasons on the same input, so
                # a single case-level value would be wrong for at least one column.
                # The case-level `expected.reason` string stays documentation.
                expected_reasons = expected_profile.get("reasons")
                expected_reasons = (
                    tuple(sorted(expected_reasons)) if expected_reasons is not None else None
                )
                expected_tokens = _normalize_tokens(expected_profile.get("affected_tokens"))

                if status != "RAN":
                    outcomes.append(
                        ProfileOutcome(
                            profile=profile,
                            status=status,
                            expected_decision=expected_decision,
                            actual_decision=None,
                            expected_memory_aware=expected_memory_aware,
                            actual_memory_aware=None,
                            classification=None,
                            reason=reason,
                            expected_reasons=expected_reasons,
                            expected_affected_tokens=expected_tokens,
                        )
                    )
                    continue

                decision, decision_reason = overall_decision(trace)
                off_trace = traces.get("off")
                off_memory_aware = off_trace.memory_aware if off_trace else None
                classification = _classify(
                    decision, trace.memory_aware, expected_decision, expected_memory_aware, off_memory_aware
                )
                actual_reasons = _decisive_reasons(trace)
                actual_tokens = _applied_tokens(trace)

                failures = list(setup_failure)
                if decision != expected_decision:
                    failures.append(f"decision expected {expected_decision}, got {decision}")
                if expected_memory_aware is not None and trace.memory_aware != expected_memory_aware:
                    failures.append("memory_aware text mismatch")
                if expected_reasons is not None and tuple(actual_reasons) != expected_reasons:
                    failures.append(
                        f"reasons expected {list(expected_reasons)}, got {list(actual_reasons)}"
                    )
                if expected_tokens is not None and actual_tokens != expected_tokens:
                    failures.append(
                        f"affected_tokens expected {list(expected_tokens)}, got {list(actual_tokens)}"
                    )

                outcomes.append(
                    ProfileOutcome(
                        profile=profile,
                        status="PASS" if not failures else "FAIL",
                        expected_decision=expected_decision,
                        actual_decision=decision,
                        expected_memory_aware=expected_memory_aware,
                        actual_memory_aware=trace.memory_aware,
                        classification=classification,
                        reason=decision_reason,
                        latency_ms=trace.latency_ms,
                        model_calls=trace.model_calls,
                        memory_ids_used=trace.memories_used,
                        expected_reasons=expected_reasons,
                        actual_reasons=actual_reasons,
                        expected_affected_tokens=expected_tokens,
                        actual_affected_tokens=actual_tokens,
                        assertion_failures=tuple(failures),
                    )
                )
            return CaseOutcome(
                id=case["id"],
                family=case.get("family", ""),
                memory_row_count=row_count,
                profiles=outcomes,
                expected_memory_row_count=None if expected_rows is None else int(expected_rows),
                setup_ok=setup_ok,
            )
        finally:
            store.close()


def run_eval(profiles: list[str], cases_dir: Path = EVAL_CASES_DIR) -> list[CaseOutcome]:
    return [run_case(case, profiles) for case in load_cases(cases_dir)]


def _summarize(case_outcomes: list[CaseOutcome], profiles: list[str]) -> dict[str, Any]:
    summary: dict[str, dict[str, Any]] = {
        profile: {
            "PASS": 0,
            "FAIL": 0,
            "SKIPPED": 0,
            "ERROR": 0,
            "useful_apply": 0,
            "unnecessary_apply": 0,
            "incorrect_apply": 0,
            "expected_abstain": 0,
            "unexpected_abstain": 0,
            "total_latency_ms": 0.0,
            "model_calls": 0,
        }
        for profile in profiles
    }
    for case in case_outcomes:
        for po in case.profiles:
            row = summary.setdefault(
                po.profile,
                {
                    "PASS": 0,
                    "FAIL": 0,
                    "SKIPPED": 0,
                    "ERROR": 0,
                    "useful_apply": 0,
                    "unnecessary_apply": 0,
                    "incorrect_apply": 0,
                    "expected_abstain": 0,
                    "unexpected_abstain": 0,
                    "total_latency_ms": 0.0,
                    "model_calls": 0,
                },
            )
            row[po.status] = row.get(po.status, 0) + 1
            if po.classification:
                row[po.classification] = row.get(po.classification, 0) + 1
            row["total_latency_ms"] += po.latency_ms
            row["model_calls"] += po.model_calls
            if po.expected_reasons is not None:
                row["asserts_reasons"] = row.get("asserts_reasons", 0) + 1
            if po.expected_affected_tokens is not None:
                row["asserts_tokens"] = row.get("asserts_tokens", 0) + 1
    for row in summary.values():
        row.setdefault("asserts_reasons", 0)
        row.setdefault("asserts_tokens", 0)
    return summary


def _assertion_coverage(case_outcomes: list[CaseOutcome]) -> dict[str, Any]:
    """How much of the suite checks *why*, not just *what*.

    A suite where this is near zero can be fully green while the cue gate, the
    conflict rule and the grapheme gate have all been deleted.
    """
    total = len(case_outcomes)
    with_reasons = sum(
        1 for c in case_outcomes if any(p.expected_reasons is not None for p in c.profiles)
    )
    with_tokens = sum(
        1 for c in case_outcomes if any(p.expected_affected_tokens is not None for p in c.profiles)
    )
    with_rows = sum(1 for c in case_outcomes if c.expected_memory_row_count is not None)
    weak = [
        c.id
        for c in case_outcomes
        if not any(p.expected_reasons is not None for p in c.profiles)
        and c.expected_memory_row_count is None
    ]
    return {
        "cases": total,
        "asserting_reasons": with_reasons,
        "asserting_affected_tokens": with_tokens,
        "asserting_memory_row_count": with_rows,
        "setup_mismatches": sum(1 for c in case_outcomes if not c.setup_ok),
        "cases_asserting_decision_and_text_only": weak,
    }


def _to_json(case_outcomes: list[CaseOutcome], profiles: list[str]) -> dict[str, Any]:
    return {
        "profiles": profiles,
        "cases": [
            {
                "id": c.id,
                "family": c.family,
                "memory_row_count": c.memory_row_count,
                "expected_memory_row_count": c.expected_memory_row_count,
                "setup_ok": c.setup_ok,
                "profiles": [
                    {
                        "profile": po.profile,
                        "status": po.status,
                        "expected_decision": po.expected_decision,
                        "actual_decision": po.actual_decision,
                        "expected_memory_aware": po.expected_memory_aware,
                        "actual_memory_aware": po.actual_memory_aware,
                        "classification": po.classification,
                        "reason": po.reason,
                        "expected_reasons": (
                            list(po.expected_reasons) if po.expected_reasons is not None else None
                        ),
                        "actual_reasons": list(po.actual_reasons),
                        "expected_affected_tokens": (
                            [dict(t) for t in po.expected_affected_tokens]
                            if po.expected_affected_tokens is not None
                            else None
                        ),
                        "actual_affected_tokens": [dict(t) for t in po.actual_affected_tokens],
                        "assertion_failures": list(po.assertion_failures),
                        "latency_ms": po.latency_ms,
                        "model_calls": po.model_calls,
                        "memory_ids_used": list(po.memory_ids_used),
                    }
                    for po in c.profiles
                ],
            }
            for c in case_outcomes
        ],
        "summary": _summarize(case_outcomes, profiles),
        "assertion_coverage": _assertion_coverage(case_outcomes),
    }


def _to_markdown(report: dict[str, Any]) -> str:
    lines = ["# Kivi eval results", ""]
    lines.append(f"Profiles: {', '.join(report['profiles'])}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| profile | pass | fail | skipped | error | useful | unnecessary | incorrect | "
        "expected_abstain | unexpected_abstain | model_calls | total_latency_ms |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for profile, row in report["summary"].items():
        lines.append(
            f"| {profile} | {row['PASS']} | {row['FAIL']} | {row['SKIPPED']} | {row['ERROR']} | "
            f"{row['useful_apply']} | {row['unnecessary_apply']} | {row['incorrect_apply']} | "
            f"{row['expected_abstain']} | {row['unexpected_abstain']} | {row['model_calls']} | "
            f"{row['total_latency_ms']:.2f} |"
        )
    lines.append("")
    cov = report.get("assertion_coverage")
    if cov:
        lines.append("## Assertion coverage")
        lines.append("")
        lines.append(
            f"Of {cov['cases']} cases: {cov['asserting_reasons']} assert *why* "
            f"(reason strings), {cov['asserting_affected_tokens']} assert which tokens "
            f"changed, {cov['asserting_memory_row_count']} assert what the learner wrote."
        )
        weak = cov["cases_asserting_decision_and_text_only"]
        if weak:
            lines.append("")
            lines.append(
                f"{len(weak)} case(s) check only decision + text, so they cannot detect a "
                "deleted gate: " + ", ".join(f"`{w}`" for w in weak)
            )
        lines.append("")
    lines.append("## Cases")
    lines.append("")
    lines.append("| case | family | rows | profile | status | expected | actual | reason |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for case in report["cases"]:
        for po in case["profiles"]:
            lines.append(
                f"| {case['id']} | {case['family']} | {case['memory_row_count']} | {po['profile']} | "
                f"{po['status']} | {po['expected_decision']} | {po['actual_decision']} | {po['reason']} |"
            )
    lines.append("")
    return "\n".join(lines)


def write_report(case_outcomes: list[CaseOutcome], profiles: list[str], results_dir: Path = EVAL_RESULTS_DIR) -> dict[str, Any]:
    results_dir.mkdir(parents=True, exist_ok=True)
    report = _to_json(case_outcomes, profiles)
    (results_dir / "latest.json").write_text(json.dumps(report, indent=2) + "\n")
    (results_dir / "latest.md").write_text(_to_markdown(report))
    return report
