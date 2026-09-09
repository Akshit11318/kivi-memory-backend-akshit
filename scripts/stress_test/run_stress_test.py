#!/usr/bin/env python3
"""Run the stress-test corpus through the real `kivi` CLI and report every
metric: hits (TP/FP/FN, precision/recall), corrections made, latency
(sum/avg/min/max), model calls, token usage, and an estimated cost.

Isolated SQLite at scripts/stress_test/stress.sqlite -- wiped and re-taught
(partially -- see vocab_manifest.json) at the start of every run. Never
touches your live notebook.

Usage:
    uv run python scripts/stress_test/generate_corpus.py   # once, or to regenerate
    uv run python scripts/stress_test/run_stress_test.py --limit 10              # ungated latency
    uv run python scripts/stress_test/run_stress_test.py --decide ungated         # full ungated
    uv run python scripts/stress_test/run_stress_test.py --decide llm --limit 10  # gated (needs key+model)

The full corpus is ~180 paragraphs. Each paragraph with 1+ surviving
candidates makes **one** LLM call for the whole string (every memory,
every repeat -- see decide/llm_helper.py), not one call per word. Use
--limit to control cost/time; the pricing table below is a rough
estimate -- verify against current provider pricing before trusting $.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from kivi_memory.pipeline.align import stitch, tokenize

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
CORPUS_PATH = OUT_DIR / "corpus.txt"
GROUND_TRUTH_PATH = OUT_DIR / "ground_truth.json"
TEACHES_PATH = OUT_DIR / "teaches.json"
DB_PATH = OUT_DIR / "stress.sqlite"
RESULTS_DIR = OUT_DIR / "results"

# Rough estimate only -- $ per 1M tokens (input, output). Verify against
# the provider's current page before treating the $ figure as authoritative.
# Unlisted models report token counts but skip the cost line.
PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "openai/gpt-oss-20b": (0.10, 0.50),
    "openai/gpt-oss-120b": (0.15, 0.75),
}

# Last-vote reasons, in the words the report uses.
REASON_LABELS = {
    "ungated": "rewrote, no sense check",
    "llm_ok": "model: same sense as the taught spelling",
    "sense_mismatch": "model: different sense, left alone",
    "llm_unavailable": "model missing, timed out, or unusable reply",
    "already_canonical": "already spelled as stored",
    "no_memory": "no notebook row",
    "conflicting_canonicals": "two stored spellings for one surface",
    "low_confidence": "memory too weak to rewrite",
}


def kivi(*args: str) -> Any:
    cmd = ["uv", "run", "kivi", "--db", str(DB_PATH), *args]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"$ {' '.join(cmd)}", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"kivi {args} exited {result.returncode}")
    text = result.stdout.strip()
    return json.loads(text) if text else None


def load_corpus() -> list[str]:
    return [line for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_ground_truth() -> list[dict]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def load_teaches() -> list[dict]:
    return json.loads(TEACHES_PATH.read_text(encoding="utf-8"))


def teach(entries: list[dict]) -> None:
    print(f"--- TEACHING ({len(entries)} partial observations) ---")
    for entry in entries:
        args = [
            "observe",
            "--source",
            "dictionary_add",
            "--user-id",
            entry["user_id"],
            "--canonical",
            entry["canonical"],
            "--forms",
            ",".join(entry["forms"]),
        ]
        if entry.get("context"):
            args += ["--context", entry["context"]]
        kivi(*args)
    print(f"taught {len(entries)} memories\n")


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    f, c = int(k), min(int(k) + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (k - f) * (ordered[c] - ordered[f])


def _hit_pairs(hits: list[dict]) -> list[tuple[str, str]]:
    return [(h["from"], h["to"]) for h in hits]


def _apply_hits(formatted: str, hits: list[tuple[str, str]]) -> str:
    """Build the expected third transcript by applying from→to in order."""
    remaining = Counter(hits)
    tokens = tokenize(formatted)
    cores: list[str] = []
    for tok in tokens:
        chosen: tuple[str, str] | None = None
        for pair in remaining:
            if remaining[pair] and pair[0] == tok.core:
                chosen = pair
                break
        if chosen is None:
            cores.append(tok.core)
            continue
        remaining[chosen] -= 1
        cores.append(chosen[1])
    return stitch(tokens, cores)


def _fmt_pairs(pairs: list[tuple[str, str]]) -> str:
    return "; ".join(f"{src} → {dst}" for src, dst in pairs)


def _row_status(extra: int, missed: int) -> str:
    if extra == 0 and missed == 0:
        return "ok"
    if extra and missed:
        return "mixed"
    if extra:
        return "extra"
    return "missed"


def _changed_line(
    found_pairs: list[tuple[str, str]],
    extra_pairs: list[tuple[str, str]],
    missed_pairs: list[tuple[str, str]],
) -> str:
    parts = []
    if found_pairs:
        parts.append("found: " + _fmt_pairs(found_pairs))
    if extra_pairs:
        parts.append("extra: " + _fmt_pairs(extra_pairs))
    if missed_pairs:
        parts.append("missed: " + _fmt_pairs(missed_pairs))
    return " | ".join(parts) if parts else "(no rewrite expected or made)"


def _take_matching(
    ordered: list[tuple[str, str]], wanted: Counter[tuple[str, str]]
) -> list[tuple[str, str]]:
    leftover = wanted.copy()
    out: list[tuple[str, str]] = []
    for pair in ordered:
        if leftover[pair]:
            out.append(pair)
            leftover[pair] -= 1
    return out


def run_corpus(
    paragraphs: list[str],
    ground_truth: list[dict],
    user_id: str = "stress",
    decide: str = "ungated",
) -> dict:
    per_paragraph: list[dict] = []
    latencies: list[float] = []
    tp = fp = fn = 0
    total_tokens_seen = 0
    total_candidates = 0
    total_applied = 0
    total_model_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    helper_llm = 0
    helper_ungated = 0
    helper_none = 0
    reason_counts: Counter[str] = Counter()
    model_seen: str | None = None
    llm_latencies: list[float] = []
    wall_start = time.perf_counter()

    for gt in ground_truth:
        idx = gt["paragraph"]
        formatted = paragraphs[idx]
        trace = kivi(
            "--profile",
            "auto",
            "--decide",
            decide,
            "run",
            "--user-id",
            user_id,
            "--formatted",
            formatted,
            "--json",
        )

        actual_pairs = [
            (d["token"], d["canonical"])
            for d in trace["decisions"]
            if d["decision"] == "APPLY" and d["canonical"]
        ]
        expected_pairs = _hit_pairs(gt["expected_hits"])
        actual = Counter(actual_pairs)
        expected = Counter(expected_pairs)
        row_tp = sum((expected & actual).values())
        row_fp = sum((actual - expected).values())
        row_fn = sum((expected - actual).values())
        tp += row_tp
        fp += row_fp
        fn += row_fn

        found_pairs = _take_matching(expected_pairs, expected & actual)
        extra_pairs = _take_matching(actual_pairs, actual - expected)
        missed_pairs = _take_matching(expected_pairs, expected - actual)
        predicted = trace["memory_aware"]
        expected_text = _apply_hits(formatted, expected_pairs)

        total_tokens_seen += len(trace["decisions"])
        total_candidates += sum(1 for d in trace["decisions"] if d["memory_ids"])
        total_applied += sum(1 for d in trace["decisions"] if d["decision"] == "APPLY")
        total_model_calls += trace["model_calls"]
        total_prompt_tokens += trace.get("prompt_tokens", 0)
        total_completion_tokens += trace.get("completion_tokens", 0)
        latencies.append(trace["latency_ms"])
        for d in trace["decisions"]:
            if d.get("memory_ids") or d.get("helper"):
                if d.get("reason"):
                    reason_counts[d["reason"]] += 1
            if d["helper"] == "llm":
                helper_llm += 1
                model_seen = d["model"] or model_seen
                if d.get("llm_latency_ms"):
                    llm_latencies.append(float(d["llm_latency_ms"]))
            elif d["helper"] == "ungated":
                helper_ungated += 1
            else:
                helper_none += 1

        per_paragraph.append(
            {
                "paragraph": idx,
                "status": _row_status(row_fp, row_fn),
                "formatted": formatted,
                "expected": expected_text,
                "predicted": predicted,
                "expected_rewrites": _fmt_pairs(expected_pairs),
                "kivi_rewrites": _fmt_pairs(actual_pairs),
                "changed": _changed_line(found_pairs, extra_pairs, missed_pairs),
                "found": row_tp,
                "extra": row_fp,
                "missed": row_fn,
                "tp": row_tp,
                "fp": row_fp,
                "fn": row_fn,
                "latency_ms": trace["latency_ms"],
                "rewritten": len(actual_pairs),
                "http_calls": trace["model_calls"],
            }
        )

        if (idx + 1) % 20 == 0 or idx == len(ground_truth) - 1:
            print(f"  ... {idx + 1}/{len(ground_truth)} paragraphs")

    wall_ms = (time.perf_counter() - wall_start) * 1000
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0

    cost_usd = None
    if model_seen and model_seen in PRICING_PER_MILLION_TOKENS and (total_prompt_tokens or total_completion_tokens):
        in_rate, out_rate = PRICING_PER_MILLION_TOKENS[model_seen]
        cost_usd = (total_prompt_tokens / 1_000_000) * in_rate + (total_completion_tokens / 1_000_000) * out_rate

    return {
        "decide": decide,
        "last_vote": "sense check" if decide == "llm" else "skip model (latency path)",
        "paragraphs": len(ground_truth),
        "tokens_seen": total_tokens_seen,
        "candidates_found": total_candidates,
        "rewritten": total_applied,
        "corrections_applied": total_applied,
        "found": tp,
        "extra": fp,
        "missed": fn,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "latency_ms_sum": sum(latencies),
        "latency_ms_mean": mean(latencies) if latencies else 0.0,
        "latency_ms_median": median(latencies) if latencies else 0.0,
        "latency_ms_p95": _percentile(latencies, 0.95),
        "latency_ms_max": max(latencies) if latencies else 0.0,
        "llm_latency_ms_mean": mean(llm_latencies) if llm_latencies else 0.0,
        "llm_latency_ms_max": max(llm_latencies) if llm_latencies else 0.0,
        "wall_ms": wall_ms,
        "http_calls": total_model_calls,
        "model_calls": total_model_calls,
        "last_vote_model": helper_llm,
        "last_vote_skip_model": helper_ungated,
        "cheap_door": helper_none,
        "helper_llm": helper_llm,
        "helper_ungated": helper_ungated,
        "reason_counts": dict(reason_counts),
        "model": model_seen,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "estimated_cost_usd": cost_usd,
        "per_paragraph": per_paragraph,
    }


def _last_vote_heading(summary: dict) -> str:
    decide = summary.get("decide") or (
        "llm" if summary.get("helper_llm") or summary.get("model_calls") else "ungated"
    )
    if decide == "llm":
        model = summary.get("model") or "(no model id on the trace)"
        return f"Last vote: **sense check** (`--decide llm`)\nModel: `{model}`"
    return "Last vote: **skip model** (`--decide ungated`) — retrieve + cheap doors only, for latency"


def _cost_line(summary: dict) -> str:
    decide = summary.get("decide")
    calls = summary.get("http_calls", summary.get("model_calls") or 0)
    model = summary.get("model")
    if decide == "ungated" or (not calls and not summary.get("helper_llm")):
        return "Estimated cost: none — the model was not called (latency path)."
    if summary.get("estimated_cost_usd") is not None:
        return (
            f"Estimated cost: **${summary['estimated_cost_usd']:.4f}** "
            "(local price table in this script; verify against the provider)."
        )
    if calls and not summary.get("total_tokens"):
        return (
            "Estimated cost: unknown — the provider returned no usage counts "
            f"({calls} HTTP call(s) still happened)."
        )
    if model and model not in PRICING_PER_MILLION_TOKENS:
        return f"Estimated cost: unknown — `{model}` is not in the local price table."
    return "Estimated cost: unknown."


def _reason_lines(summary: dict) -> list[str]:
    counts = summary.get("reason_counts") or {}
    if not counts:
        return []
    lines = ["", "### Why each word was rewritten or left alone", ""]
    lines.append("| reason | words | meaning |")
    lines.append("| --- | ---: | --- |")
    for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        label = REASON_LABELS.get(reason, reason)
        lines.append(f"| `{reason}` | {count} | {label} |")
    return lines


def markdown_report(summary: dict) -> str:
    found = summary.get("found", summary["tp"])
    extra = summary.get("extra", summary["fp"])
    missed = summary.get("missed", summary["fn"])
    rewritten = summary.get("rewritten", summary.get("corrections_applied", 0))
    expected = found + missed
    notebook_match = summary["candidates_found"]
    http_calls = summary.get("http_calls", summary["model_calls"])
    last_vote_model = summary.get("last_vote_model", summary.get("helper_llm", 0))
    last_vote_skip = summary.get("last_vote_skip_model", summary.get("helper_ungated", 0))

    lines = [
        "# Kivi stress-test results",
        "",
        _last_vote_heading(summary),
        "",
        f"Corpus: **{summary['paragraphs']}** paragraphs, **{summary['tokens_seen']}** words scored.",
        "",
        "## Rewrites",
        "",
        "| | count | meaning |",
        "| --- | ---: | --- |",
        f"| notebook match | {notebook_match} | word had at least one stored spelling |",
        f"| rewritten | {rewritten} | the third transcript changed that word |",
        f"| expected | {expected} | rewrites the ground truth asked for |",
        f"| found | {found} | rewritten, and expected (true positive) |",
        f"| extra | {extra} | rewritten, but not expected (false positive) |",
        f"| missed | {missed} | expected, but left unchanged (false negative) |",
        "",
        f"Precision **{summary['precision']:.3f}** = found / (found + extra). "
        "1.000 with rewritten = 0 only means nothing extra fired — it is not a good run.",
        "",
        f"Recall **{summary['recall']:.3f}** = found / (found + missed).",
        "",
        "## Time (ms)",
        "",
        "Pipeline time is inside one `kivi run`. Elapsed includes starting that process each paragraph.",
        "",
        "| | ms |",
        "| --- | ---: |",
        f"| typical paragraph (median) | {summary['latency_ms_median']:.1f} |",
        f"| average paragraph | {summary['latency_ms_mean']:.1f} |",
        f"| slowest paragraph | {summary['latency_ms_max']:.1f} |",
        f"| p95 paragraph | {summary['latency_ms_p95']:.1f} |",
        f"| sum of pipeline times | {summary['latency_ms_sum']:.1f} |",
        f"| elapsed (wall) | {summary['wall_ms']:.1f} |",
    ]
    if summary.get("llm_latency_ms_mean"):
        lines += [
            f"| typical model HTTP call | {summary['llm_latency_ms_mean']:.1f} |",
            f"| slowest model HTTP call | {summary['llm_latency_ms_max']:.1f} |",
        ]
    lines += _reason_lines(summary)
    lines += [
        "",
        "## Model",
        "",
        f"- HTTP calls: **{http_calls}** (one per `kivi run` that still had a survivor)",
        f"- Last vote was the model: **{last_vote_model}** words",
        f"- Last vote skipped the model: **{last_vote_skip}** words",
        f"- Prompt tokens: {summary['prompt_tokens']}, completion tokens: {summary['completion_tokens']}",
        f"- {_cost_line(summary)}",
        "",
    ]
    if rewritten == 0 and last_vote_model and (summary.get("reason_counts") or {}).get("llm_unavailable"):
        lines.append(
            "Note: every model last-vote abstained with `llm_unavailable` "
            "(timeout or unusable JSON). That is why found = 0. Try a non-thinking "
            "model such as `accounts/fireworks/routers/glm-5p2-fast`."
        )
        lines.append("")
    elif rewritten == 0 and last_vote_model and not last_vote_skip:
        lines.append(
            "Note: the model was asked, and nothing was rewritten. Check the reason "
            "table — `llm_unavailable` means the reply was empty or unusable; "
            "`sense_mismatch` means the model voted no."
        )
        lines.append("")
    lines += _cases_markdown(summary.get("per_paragraph") or [])
    return "\n".join(lines)


def _md_cell(text: str, limit: int = 160) -> str:
    clipped = " ".join(text.split())
    if len(clipped) > limit:
        clipped = clipped[: limit - 1] + "…"
    return clipped.replace("|", "\\|")


def _cases_markdown(rows: list[dict]) -> list[str]:
    if not rows or "formatted" not in rows[0]:
        return []
    fails = [r for r in rows if r.get("status") and r["status"] != "ok"]
    lines = [
        "",
        "## Paragraphs",
        "",
        "Full text is in `latest.cases.csv`. This table is the short view; "
        "failing rows are expanded below.",
        "",
        "| # | status | found | extra | missed | what changed |",
        "| ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['paragraph']} | {row.get('status', '')} | {row.get('found', row.get('tp', 0))} | "
            f"{row.get('extra', row.get('fp', 0))} | {row.get('missed', row.get('fn', 0))} | "
            f"{_md_cell(row.get('changed') or '', 120)} |"
        )
    if not fails:
        lines += ["", "Every paragraph matched the expected rewrites.", ""]
        return lines
    lines += ["", f"## Failures ({len(fails)})", ""]
    for row in fails:
        lines += [
            f"### Paragraph {row['paragraph']} — `{row['status']}`",
            "",
            f"What changed: {row.get('changed') or '(none)'}",
            "",
            "| | text |",
            "| --- | --- |",
            f"| formatted | {_md_cell(row['formatted'], 800)} |",
            f"| expected | {_md_cell(row['expected'], 800)} |",
            f"| kivi | {_md_cell(row['predicted'], 800)} |",
            "",
        ]
    return lines


CASES_CSV_FIELDS = [
    "paragraph",
    "status",
    "formatted",
    "expected",
    "predicted",
    "expected_rewrites",
    "kivi_rewrites",
    "changed",
    "found",
    "extra",
    "missed",
    "latency_ms",
]


def write_cases_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CASES_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CASES_CSV_FIELDS})


def write_report(summary: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "latest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (RESULTS_DIR / "latest.md").write_text(markdown_report(summary), encoding="utf-8")
    write_cases_csv(summary.get("per_paragraph") or [], RESULTS_DIR / "latest.cases.csv")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only run the first N paragraphs")
    parser.add_argument("--user-id", default="stress")
    parser.add_argument(
        "--decide",
        default="ungated",
        choices=["llm", "ungated"],
        help="ungated = no HTTP, retrieve latency. llm = sense check (needs KIVI_LLM_API_KEY + KIVI_LLM_MODEL)",
    )
    args = parser.parse_args()

    if DB_PATH.exists():
        DB_PATH.unlink()

    paragraphs = load_corpus()
    ground_truth = load_ground_truth()
    teaches = load_teaches()
    if args.limit:
        ground_truth = ground_truth[: args.limit]

    print("=" * 100)
    print("KIVI STRESS TEST")
    if args.decide == "llm":
        print("last vote: sense check (--decide llm)")
    else:
        print("last vote: skip model (--decide ungated), latency path")
    print(f"corpus: {len(paragraphs)} paragraphs total, running {len(ground_truth)}")
    print("=" * 100)

    teach(teaches)

    print(f"--- RUNNING ({len(ground_truth)} paragraphs) ---")
    summary = run_corpus(paragraphs, ground_truth, args.user_id, decide=args.decide)
    write_report(summary)

    print()
    print("=" * 100)
    print(
        f"paragraphs={summary['paragraphs']} words={summary['tokens_seen']} "
        f"notebook_match={summary['candidates_found']} rewritten={summary['rewritten']}"
    )
    print(
        f"rewrites: found={summary['found']} extra={summary['extra']} missed={summary['missed']} "
        f"precision={summary['precision']:.3f} recall={summary['recall']:.3f}"
    )
    print(
        f"time_ms: typical={summary['latency_ms_median']:.1f} average={summary['latency_ms_mean']:.1f} "
        f"slowest={summary['latency_ms_max']:.1f} elapsed={summary['wall_ms']:.1f}"
    )
    print(
        f"http_calls={summary['http_calls']} last_vote_model={summary['last_vote_model']} "
        f"last_vote_skip_model={summary['last_vote_skip_model']} model={summary['model']}"
    )
    print(
        f"usage: prompt={summary['prompt_tokens']} completion={summary['completion_tokens']}"
    )
    if summary["estimated_cost_usd"] is not None:
        print(f"estimated_cost_usd={summary['estimated_cost_usd']:.4f} (rough -- verify current pricing)")
    print("wrote scripts/stress_test/results/latest.json, latest.md, and latest.cases.csv")
    print("=" * 100)


if __name__ == "__main__":
    main()
