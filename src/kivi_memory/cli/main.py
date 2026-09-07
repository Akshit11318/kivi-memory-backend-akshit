"""kivi CLI. I/O only — skin + flags. No policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kivi_memory.cli.art import banner, command_bench, error_line, not_built
from kivi_memory.cli.style import Ink, color_enabled
from kivi_memory.config import (
    DEFAULT_DB_PATH,
    DEFAULT_PROFILE,
    DEFAULT_USER_ID,
    PROFILES,
    SEED_PATH,
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
                        "context_cues": list(memory.context_cues),
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


def _cmd_run(args: argparse.Namespace, ink: Ink) -> int:
    with MemoryStore(Path(args.db)) as store:
        try:
            trace = run_pipeline(store, args.user_id, args.asr, args.formatted, args.profile)
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
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    unknown = [p for p in profiles if p not in PROFILES]
    if unknown:
        print(
            error_line(ink, f"unknown profile(s) {unknown}\nuse: {', '.join(PROFILES)}"),
            file=sys.stderr,
        )
        return 2

    from kivi_memory.eval_runner import run_eval, write_report

    case_outcomes = run_eval(profiles)
    report = write_report(case_outcomes, profiles)

    print(f"eval: {len(case_outcomes)} cases x {len(profiles)} profiles")
    print("wrote eval/results/latest.json and eval/results/latest.md")
    total_bad = 0
    for profile, row in report["summary"].items():
        print(
            f"  {profile:10} pass={row['PASS']} fail={row['FAIL']} "
            f"skipped={row['SKIPPED']} error={row['ERROR']}"
        )
        total_bad += row["FAIL"] + row["ERROR"]
    return 1 if total_bad else 0


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
        help="off | exact | phonetic (default exact)",
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
        help="dictionary_add: optional example sentence to scope the word (adds context_cues)",
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
    eval_p = sub.add_parser("eval", help="score fixtures")
    eval_p.add_argument("--profiles", default=",".join(PROFILES))
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
