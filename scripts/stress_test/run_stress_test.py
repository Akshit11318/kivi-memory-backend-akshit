#!/usr/bin/env python3
"""Run the stress-test corpus through the real `kivi` CLI and report every
metric: hits (TP/FP/FN, precision/recall), corrections made, latency
(sum/avg/min/max), model calls, token usage, and an estimated cost.

Isolated SQLite at scripts/stress_test/stress.sqlite -- wiped and re-taught
(partially -- see vocab_manifest.json) at the start of every run. Never
touches your live notebook.

Usage:
    uv run python scripts/stress_test/generate_corpus.py   # once, or to regenerate
    uv run python scripts/stress_test/run_stress_test.py               # ungated, free
    KIVI_LLM_API_KEY=... uv run python scripts/stress_test/run_stress_test.py            # gated
    KIVI_LLM_API_KEY=... uv run python scripts/stress_test/run_stress_test.py --limit 10  # smoke test, first 10 paragraphs

The full corpus is ~180 paragraphs. Each paragraph with 1+ ambiguous or
repeated-token candidates makes one LLM call per distinct memory (batched
across repeats -- see decide/llm_helper.py), so a full gated run is on the
order of a few dozen to ~100 real API calls, not one per word. Use --limit
to control cost/time directly; the pricing table below is a rough estimate
you should verify against current provider pricing before trusting the $
figure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
CORPUS_PATH = OUT_DIR / "corpus.txt"
GROUND_TRUTH_PATH = OUT_DIR / "ground_truth.json"
TEACHES_PATH = OUT_DIR / "teaches.json"
DB_PATH = OUT_DIR / "stress.sqlite"
RESULTS_DIR = OUT_DIR / "results"

# Rough estimate only -- $ per 1M tokens (input, output). Verify against
# https://www.anthropic.com/pricing and https://groq.com/pricing (or your
# provider's current page) before treating the cost figure as authoritative.
# Unlisted models report token counts but skip the cost line.
PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "openai/gpt-oss-20b": (0.10, 0.50),
    "openai/gpt-oss-120b": (0.15, 0.75),
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


def run_corpus(paragraphs: list[str], ground_truth: list[dict], user_id: str = "stress") -> dict:
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
    model_seen: str | None = None
    wall_start = time.perf_counter()

    for gt in ground_truth:
        idx = gt["paragraph"]
        formatted = paragraphs[idx]
        trace = kivi(
            "--profile", "auto", "run", "--user-id", user_id, "--formatted", formatted, "--json"
        )

        actual = Counter(
            (d["token"], d["canonical"])
            for d in trace["decisions"]
            if d["decision"] == "APPLY" and d["canonical"]
        )
        expected = Counter((h["from"], h["to"]) for h in gt["expected_hits"])
        row_tp = sum((expected & actual).values())
        row_fp = sum((actual - expected).values())
        row_fn = sum((expected - actual).values())
        tp += row_tp
        fp += row_fp
        fn += row_fn

        total_tokens_seen += len(trace["decisions"])
        total_candidates += sum(1 for d in trace["decisions"] if d["memory_ids"])
        total_applied += sum(1 for d in trace["decisions"] if d["decision"] == "APPLY")
        total_model_calls += trace["model_calls"]
        total_prompt_tokens += trace.get("prompt_tokens", 0)
        total_completion_tokens += trace.get("completion_tokens", 0)
        latencies.append(trace["latency_ms"])
        for d in trace["decisions"]:
            if d["helper"] == "llm":
                helper_llm += 1
                model_seen = d["model"] or model_seen
            elif d["helper"] == "ungated":
                helper_ungated += 1

        per_paragraph.append(
            {"paragraph": idx, "tp": row_tp, "fp": row_fp, "fn": row_fn, "latency_ms": trace["latency_ms"]}
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
        "paragraphs": len(ground_truth),
        "tokens_seen": total_tokens_seen,
        "candidates_found": total_candidates,
        "corrections_applied": total_applied,
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
        "wall_ms": wall_ms,
        "model_calls": total_model_calls,
        "helper_llm": helper_llm,
        "helper_ungated": helper_ungated,
        "model": model_seen,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "estimated_cost_usd": cost_usd,
        "per_paragraph": per_paragraph,
    }


def write_report(summary: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "latest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    has_key = bool(os.environ.get("KIVI_LLM_API_KEY"))
    lines = ["# Kivi stress-test results", ""]
    lines.append(f"Mode: {'GATED' if has_key else 'UNGATED'}" + (f" ({summary['model']})" if summary["model"] else ""))
    lines.append("")
    lines.append(f"**{summary['paragraphs']} paragraphs, {summary['tokens_seen']} tokens processed, "
                  f"{summary['candidates_found']} had a candidate memory, {summary['corrections_applied']} corrections applied.**")
    lines.append("")
    lines.append(f"**Hits: TP={summary['tp']} FP={summary['fp']} FN={summary['fn']} "
                  f"precision={summary['precision']:.3f} recall={summary['recall']:.3f}**")
    lines.append("")
    lines.append("## Latency (per paragraph, ms)")
    lines.append("")
    lines.append("| sum | mean | median | p95 | max | wall clock |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    lines.append(
        f"| {summary['latency_ms_sum']:.1f} | {summary['latency_ms_mean']:.1f} | "
        f"{summary['latency_ms_median']:.1f} | {summary['latency_ms_p95']:.1f} | "
        f"{summary['latency_ms_max']:.1f} | {summary['wall_ms']:.1f} |"
    )
    lines.append("")
    lines.append("## Model usage and cost")
    lines.append("")
    lines.append(f"- model_calls: {summary['model_calls']}")
    lines.append(f"- helper=llm decisions: {summary['helper_llm']}, helper=ungated decisions: {summary['helper_ungated']}")
    lines.append(f"- prompt_tokens: {summary['prompt_tokens']}, completion_tokens: {summary['completion_tokens']}, total: {summary['total_tokens']}")
    if summary["estimated_cost_usd"] is not None:
        lines.append(
            f"- **estimated cost: ${summary['estimated_cost_usd']:.4f}** "
            "(PRICING_PER_MILLION_TOKENS in this script is a rough estimate -- verify against current provider pricing)"
        )
    else:
        lines.append("- estimated cost: n/a (no key used, or model not in the local pricing table)")
    lines.append("")
    (RESULTS_DIR / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only run the first N paragraphs")
    parser.add_argument("--user-id", default="stress")
    args = parser.parse_args()

    if DB_PATH.exists():
        DB_PATH.unlink()

    paragraphs = load_corpus()
    ground_truth = load_ground_truth()
    teaches = load_teaches()
    if args.limit:
        ground_truth = ground_truth[: args.limit]

    has_key = bool(os.environ.get("KIVI_LLM_API_KEY"))
    print("=" * 100)
    print("KIVI STRESS TEST")
    print(f"mode: {'GATED (KIVI_LLM_API_KEY set)' if has_key else 'UNGATED (no key)'}")
    print(f"corpus: {len(paragraphs)} paragraphs total, running {len(ground_truth)}")
    print("=" * 100)

    teach(teaches)

    print(f"--- RUNNING ({len(ground_truth)} paragraphs) ---")
    summary = run_corpus(paragraphs, ground_truth, args.user_id)
    write_report(summary)

    print()
    print("=" * 100)
    print(
        f"paragraphs={summary['paragraphs']} tokens_seen={summary['tokens_seen']} "
        f"candidates={summary['candidates_found']} corrections={summary['corrections_applied']}"
    )
    print(
        f"hits: TP={summary['tp']} FP={summary['fp']} FN={summary['fn']} "
        f"precision={summary['precision']:.3f} recall={summary['recall']:.3f}"
    )
    print(
        f"latency_ms: sum={summary['latency_ms_sum']:.1f} mean={summary['latency_ms_mean']:.1f} "
        f"p95={summary['latency_ms_p95']:.1f} max={summary['latency_ms_max']:.1f} wall={summary['wall_ms']:.1f}"
    )
    print(
        f"model_calls={summary['model_calls']} helper_llm={summary['helper_llm']} "
        f"helper_ungated={summary['helper_ungated']} model={summary['model']}"
    )
    print(
        f"tokens: prompt={summary['prompt_tokens']} completion={summary['completion_tokens']} "
        f"total={summary['total_tokens']}"
    )
    if summary["estimated_cost_usd"] is not None:
        print(f"estimated_cost_usd={summary['estimated_cost_usd']:.4f} (rough -- verify current pricing)")
    print("wrote scripts/stress_test/results/latest.json and latest.md")
    print("=" * 100)


if __name__ == "__main__":
    main()
