"""kivi CLI. I/O only — skin + flags. No policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kivi_memory.cli.art import banner, command_bench, error_line, not_built
from kivi_memory.cli.style import Ink, color_enabled
from kivi_memory.config import (
    DECIDE_MODES,
    DEFAULT_DB_PATH,
    DEFAULT_DECIDE,
    DEFAULT_PROFILE,
    DEFAULT_USER_ID,
    PROFILES,
    SEED_PATH,
    llm_credentials,
    missing_llm_config_message,
)
from kivi_memory.learner import explicit as explicit_learner
from kivi_memory.pipeline.run import run as run_pipeline
from kivi_memory.store.db import MemoryStore
from kivi_memory.trace.format import overall_decision, trace_frame, trace_to_dict


def _ink(args: argparse.Namespace) -> Ink:
    return Ink(color_enabled(plain=getattr(args, "plain", False)))


def _cmd_reset(args: argparse.Namespace) -> int:
    with MemoryStore(Path(args.db)) as store:
        store.reset()
        if not args.seed:
            print(f"reset: wiped {store.db_path}")
            return 0

        seed_path = Path(args.seed_path)
        entries = json.loads(seed_path.read_text()) if seed_path.exists() else []
        if entries:
            from kivi_memory.learner import explicit as explicit_learner

            for entry in entries:
                explicit_learner.replay(store, entry)
        print(f"reset --seed: wiped {store.db_path}, replayed {len(entries)} observation(s)")
    return 0


def _cmd_observe(args: argparse.Namespace) -> int:
    with MemoryStore(Path(args.db)) as store:
        if args.source == "dictionary_add":
            if not args.canonical:
                print("observe dictionary_add requires --canonical", file=sys.stderr)
                return 2
            forms = [f.strip() for f in args.forms.split(",")] if args.forms else []
            forms = [f for f in forms if f]
            memory = explicit_learner.dictionary_add(
                store, args.user_id, args.canonical, forms, args.context
            )
            print(
                json.dumps(
                    {
                        "learned": True,
                        "canonical": memory.canonical,
                        "forms": list(memory.forms),
                        "confidence": memory.confidence,
                        "teach_text": memory.teach_text,
                    },
                    indent=2,
                )
            )
            return 0

        if args.source == "correction":
            if not args.formatted or not args.final:
                print("observe correction requires --formatted and --final", file=sys.stderr)
                return 2
            outcomes = explicit_learner.correction(
                store, args.user_id, args.formatted, args.final, args.asr
            )
            print(
                json.dumps(
                    [
                        {
                            "formatted_word": o.formatted_word,
                            "final_word": o.final_word,
                            "learned": o.learned,
                            "reason": o.reason,
                            "canonical": o.memory.canonical if o.memory else None,
                            "confidence": o.memory.confidence if o.memory else None,
                        }
                        for o in outcomes
                    ],
                    indent=2,
                )
            )
            return 0

        print(f"observe: unknown --source {args.source!r} (use dictionary_add | correction)", file=sys.stderr)
        return 2


def _needs_llm(args: argparse.Namespace) -> bool:
    if args.command not in ("run", "eval"):
        return False
    if args.command == "run" and args.profile == "off":
        return False
    return args.decide == "llm"


def _cmd_run(args: argparse.Namespace, ink: Ink) -> int:
    with MemoryStore(Path(args.db)) as store:
        try:
            trace = run_pipeline(
                store,
                args.user_id,
                args.asr,
                args.formatted,
                args.profile,
                decide=args.decide,
            )
        except NotImplementedError as exc:
            print(error_line(ink, str(exc)), file=sys.stderr)
            return 2

    if args.json:
        print(json.dumps(trace_to_dict(trace), indent=2))
        return 0

    decision, reason = overall_decision(trace)
    print(
        trace_frame(
            ink,
            asr=trace.asr,
            formatted=trace.formatted,
            decision=decision,
            memory_aware=trace.memory_aware,
            reason=reason,
            profile=trace.profile,
        )
    )
    return 0


def _cmd_eval(args: argparse.Namespace, ink: Ink) -> int:
    from kivi_memory.eval_runner import run_eval, write_report

    results = run_eval(decide=args.decide)
    report = write_report(results)
    totals = report["summary"]["totals"]

    print(
        f"eval: {len(results)} rows -> "
        f"expected_hits={totals['expected_hits']} actual_hits={totals['actual_hits']} "
        f"TP={totals['tp']} FP={totals['fp']} FN={totals['fn']} "
        f"precision={totals['precision']:.2f} recall={totals['recall']:.2f}"
    )
    print(
        f"  ran={totals['ran']} skipped={totals['skipped']} errors={totals['errors']} "
        f"string_mismatches={totals['string_mismatches']} "
        f"model_calls={totals['model_calls']} helper_llm={totals['helper_llm']} "
        f"helper_ungated={totals['helper_ungated']}"
    )
    print(
        f"  time_ms: typical={totals['latency_ms_median']:.1f} "
        f"average={totals['latency_ms_mean']:.1f} "
        f"p95={totals['latency_ms_p95']:.1f} "
        f"slowest={totals['latency_ms_max']:.1f} "
        f"sum={totals['latency_ms']:.1f}"
    )
    if totals.get("rows_with_llm_call"):
        print(
            f"  llm_ms: typical={totals['llm_latency_ms_mean']:.1f} "
            f"slowest={totals['llm_latency_ms_max']:.1f} "
            f"rows={int(totals['rows_with_llm_call'])}"
        )
    print("wrote eval/results/latest.json and eval/results/latest.md")
    return 1 if (totals["string_mismatches"] or totals["errors"]) else 0


def _cmd_memories(args: argparse.Namespace) -> int:
    with MemoryStore(Path(args.db)) as store:
        memories = store.list_memories()
        payload = [
            {
                "id": memory.id,
                "user_id": memory.user_id,
                "canonical": memory.canonical,
                "forms": list(memory.forms),
                "confidence": memory.confidence,
                "teach_text": memory.teach_text,
            }
            for memory in memories
        ]
        print(json.dumps(payload, indent=2))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kivi",
        description="A small notebook for names, places, and pet words.",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="SQLite path (default data/kivi.sqlite)",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help="off | exact | phonetic | auto (default auto)",
    )
    parser.add_argument(
        "--decide",
        default=DEFAULT_DECIDE,
        help="llm | ungated (default llm). llm requires KIVI_LLM_API_KEY and "
        "KIVI_LLM_MODEL. ungated skips the model so you can measure retrieve latency.",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="no color or box drawing",
    )
    sub = parser.add_subparsers(dest="command")

    observe = sub.add_parser("observe", help="put a spelling in the notebook")
    observe.add_argument("--source", required=True, choices=["dictionary_add", "correction"])
    observe.add_argument("--user-id", dest="user_id", default=DEFAULT_USER_ID)
    observe.add_argument("--canonical", default=None, help="dictionary_add: the written form")
    observe.add_argument("--forms", default=None, help="dictionary_add: comma-separated surfaces")
    observe.add_argument(
        "--context",
        default=None,
        help="dictionary_add: optional example sentence, stored as teach_text evidence "
        "for the LLM sense helper (not a gate)",
    )
    observe.add_argument("--formatted", default=None, help="correction: formatter output")
    observe.add_argument("--final", default=None, help="correction: the user's corrected text")
    observe.add_argument("--asr", default=None, help="correction: optional raw ASR, stored not mined")

    sub.add_parser("memories", help="open what you have kept")
    run = sub.add_parser("run", help="try a new line")
    run.add_argument("--asr", default="")
    run.add_argument("--formatted", default="")
    run.add_argument("--user-id", dest="user_id", default=DEFAULT_USER_ID)
    run.add_argument("--json", action="store_true", help="print the full inspectable trace as JSON")
    sub.add_parser("eval", help="score eval/dataset/*.csv, write eval/results/latest.{json,md}")
    reset = sub.add_parser("reset", help="clear the page; --seed to refill")
    reset.add_argument("--seed", action="store_true")
    reset.add_argument("--seed-path", default=str(SEED_PATH))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    ink = _ink(args)

    if args.command is None:
        sys.stdout.write(banner(ink, profile=args.profile))
        sys.stdout.write(command_bench(ink))
        return 0

    if args.profile not in PROFILES:
        print(
            error_line(
                ink,
                f"unknown profile {args.profile!r}\nuse: {', '.join(PROFILES)}",
            ),
            file=sys.stderr,
        )
        return 2

    if args.decide not in DECIDE_MODES:
        print(
            error_line(
                ink,
                f"unknown decide {args.decide!r}\nuse: {', '.join(DECIDE_MODES)}",
            ),
            file=sys.stderr,
        )
        return 2

    if _needs_llm(args) and llm_credentials() is None:
        print(missing_llm_config_message(), file=sys.stderr)
        return 2

    if args.command == "observe":
        return _cmd_observe(args)
    if args.command == "run":
        return _cmd_run(args, ink)
    if args.command == "eval":
        return _cmd_eval(args, ink)
    if args.command == "reset":
        return _cmd_reset(args)
    if args.command == "memories":
        return _cmd_memories(args)

    sys.stdout.write(banner(ink, profile=args.profile))
    print(not_built(ink, args.command))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
