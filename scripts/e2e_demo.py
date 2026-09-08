#!/usr/bin/env python3
"""End-to-end memory training + testing demo, driving the real `kivi` CLI.

Trains a handful of memories (dictionary_add + correction, including one
deliberate learner refusal), then runs a set of long, unique paragraphs
through `kivi --profile auto run --json` and prints, for every test:

  - the memory-aware output (the "third transcript")
  - the full per-token annotation trace for every token that matched a
    memory: decision, reason, matched_via (exact|phonetic), helper
    (llm|ungated|null), model, and the LLM call's own latency
  - the run's total latency_ms and model_calls

Isolated SQLite at data/e2e_demo.sqlite -- never touches your live notebook
at data/kivi.sqlite. Safe to re-run any time; wipes and re-trains from
scratch on every invocation.

Usage:
    uv run python scripts/e2e_demo.py

Set KIVI_LLM_API_KEY first (any OpenAI-compatible host, see .env.example)
to exercise the gated LLM sense helper instead of the ungated default --
everything else about the run is identical. Compare the two:

    uv run python scripts/e2e_demo.py                    # ungated
    KIVI_LLM_API_KEY=... uv run python scripts/e2e_demo.py  # gated
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "e2e_demo.sqlite"


def kivi(*args: str) -> Any:
    """Run `uv run kivi --db <demo db> <args>` and return parsed JSON stdout."""
    cmd = ["uv", "run", "kivi", "--db", str(DB_PATH), *args]
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"$ {' '.join(cmd)}", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"kivi {args} exited {result.returncode}")
    text = result.stdout.strip()
    return json.loads(text) if text else None


# label, cli args for `kivi observe ...`
TRAIN: list[tuple[str, list[str]]] = [
    (
        "Kivi: product/fruit homograph, taught with context",
        [
            "observe", "--source", "dictionary_add",
            "--canonical", "Kivi", "--forms", "kivi,kiwi",
            "--context", "Our platform Kivi handles ASR post-processing for enterprise clients.",
        ],
    ),
    (
        "Groww: brand/verb homograph, taught with context",
        [
            "observe", "--source", "dictionary_add",
            "--canonical", "Groww", "--forms", "grow,groww",
            "--context", "He opened a mutual fund SIP on Groww last month.",
        ],
    ),
    (
        "Ankita: personal name respelling via correction",
        [
            "observe", "--source", "correction",
            "--formatted", "Please sync with Ankeeta about the quarterly roadmap review.",
            "--final", "Please sync with Ankita about the quarterly roadmap review.",
        ],
    ),
    (
        "Grafana: phonetic-only, no teach_text",
        ["observe", "--source", "dictionary_add", "--canonical", "Grafana", "--forms", "grafana"],
    ),
    (
        "Sanya/Sania: two canonicals claim one surface (conflict setup, half 1)",
        ["observe", "--source", "dictionary_add", "--canonical", "Sanya", "--forms", "sania"],
    ),
    (
        "Sanya/Sania: conflict setup, half 2",
        ["observe", "--source", "dictionary_add", "--canonical", "Sania", "--forms", "sanya"],
    ),
    (
        "Deliberate refusal: content edit (Tuesday->Thursday), must learn 0 rows",
        [
            "observe", "--source", "correction",
            "--formatted", "The vendor confirmed the shipment will arrive on Tuesday.",
            "--final", "The vendor confirmed the shipment will arrive on Thursday.",
        ],
    ),
]

# label, asr, formatted
TESTS: list[tuple[str, str, str]] = [
    (
        "Alignment + multi-mention (contraction expansion, one name twice)",
        "im gonna loop in ankeeta and the vendor team before the sync tomorrow "
        "morning and ill make sure ankeeta has the latest roadmap doc ready",
        "I'm going to loop in Ankeeta and the vendor team before the sync "
        "tomorrow morning, and I'll make sure Ankeeta has the latest roadmap "
        "doc ready.",
    ),
    (
        "Phonetic cascade, zero-shot misspelling exact never saw",
        "",
        "Please restart the grafanna dashboard before the incident review, "
        "since the grafanna alerts have been silent since last night's deploy.",
    ),
    (
        "Sense check: fruit -- expect ABSTAIN with a key, APPLY (ungated) without",
        "",
        "For the picnic on Saturday we should pack some kiwi, grapes, and "
        "maybe a fruit salad since the kids love kiwi so much.",
    ),
    (
        "Sense check: product, zero shared vocabulary with the teach sentence",
        "",
        "The on-call engineer restarted the kiwi ingestion worker after the "
        "nightly batch job failed twice in staging.",
    ),
    (
        "Sense check: common verb -- expect ABSTAIN with a key, APPLY (ungated) without",
        "",
        "With consistent watering and enough sunlight, the tomato saplings "
        "in the backyard garden should grow within a few weeks.",
    ),
    (
        "Sense check: brand, zero shared vocabulary with the teach sentence",
        "",
        "My cousin just moved his entire stock portfolio to grow after "
        "reading great reviews online.",
    ),
    (
        "Conflicting canonicals: must ABSTAIN, never rank by confidence",
        "",
        "Sania confirmed she'll present the design review slides during "
        "tomorrow's stakeholder sync.",
    ),
    (
        "Deliberate no-op: long paragraph sharing no vocabulary with the notebook",
        "",
        "The quarterly all-hands meeting has been rescheduled to next Friday "
        "afternoon, and attendance is optional for remote employees who are "
        "traveling this week.",
    ),
]


def _fmt(value: Any, width: int) -> str:
    return f"{str(value):<{width}}"


def _fmt_ms(value: float | None) -> str:
    return f"{value:.1f}ms" if value is not None else "-"


def run_training() -> None:
    print("\n--- TRAINING (kivi observe) ---\n")
    for label, args in TRAIN:
        result = kivi(*args)
        print(f"[teach] {label}")
        if args[2] == "dictionary_add":
            print(
                f"        -> canonical={result['canonical']!r} forms={result['forms']} "
                f"confidence={result['confidence']} teach_text={result['teach_text']!r}"
            )
        else:
            for outcome in result:
                if outcome["learned"]:
                    print(
                        f"        -> learned {outcome['formatted_word']!r} -> "
                        f"{outcome['final_word']!r} (confidence={outcome['confidence']})"
                    )
                else:
                    print(
                        f"        -> refused {outcome['formatted_word']!r} -> "
                        f"{outcome['final_word']!r} (reason={outcome['reason']})"
                    )
        print()


def run_tests() -> None:
    print("\n--- TESTING (kivi --profile auto run --json) ---\n")
    total_latency_ms = 0.0
    total_model_calls = 0
    total_wall_ms = 0.0

    for i, (label, asr, formatted) in enumerate(TESTS, 1):
        start = time.perf_counter()
        trace = kivi("--profile", "auto", "run", "--asr", asr, "--formatted", formatted, "--json")
        wall_ms = (time.perf_counter() - start) * 1000

        print(f"### TEST {i}: {label}")
        if asr:
            print(f"IN  (asr):       {asr}")
        print(f"IN  (formatted): {formatted}")
        print(f"OUT (memory-aware): {trace['memory_aware']}")
        print(
            f"latency_ms={trace['latency_ms']:.2f}  model_calls={trace['model_calls']}  "
            f"wall_ms={wall_ms:.1f} (includes CLI process startup)"
        )

        annotated = [d for d in trace["decisions"] if d["memory_ids"]]
        if annotated:
            print("annotations (tokens that matched a memory):")
            for d in annotated:
                print(
                    f"  [{d['index']:>2}] {_fmt(repr(d['token']), 16)} "
                    f"decision={_fmt(d['decision'], 8)} "
                    f"reason={_fmt(d['reason'], 26)[:26]} "
                    f"matched_via={_fmt(d['matched_via'], 9)} "
                    f"helper={_fmt(d['helper'], 8)} "
                    f"model={_fmt(d['model'], 26)} "
                    f"llm_latency={_fmt_ms(d['llm_latency_ms'])}"
                )
        else:
            print("annotations: (no token matched a memory -- pure no-op)")
        print()

        total_latency_ms += trace["latency_ms"]
        total_model_calls += trace["model_calls"]
        total_wall_ms += wall_ms

    print("=" * 100)
    print(
        f"TOTAL: {len(TESTS)} tests | pipeline latency_ms sum={total_latency_ms:.2f} | "
        f"model_calls sum={total_model_calls} | wall_ms sum={total_wall_ms:.1f} "
        f"(includes {len(TESTS)}x CLI process startup)"
    )
    print("=" * 100)


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    has_key = bool(os.environ.get("KIVI_LLM_API_KEY"))
    model = os.environ.get("KIVI_LLM_MODEL", "openai/gpt-oss-20b")
    print("=" * 100)
    print("KIVI END-TO-END DEMO — training then testing, via the real `kivi` CLI")
    print(f"mode:  {'GATED  (KIVI_LLM_API_KEY set, model=' + model + ')' if has_key else 'UNGATED (no KIVI_LLM_API_KEY)'}")
    print(f"db:    {DB_PATH.relative_to(REPO_ROOT)}  (isolated demo store, wiped at start of this run)")
    print("=" * 100)

    run_training()
    run_tests()


if __name__ == "__main__":
    main()
