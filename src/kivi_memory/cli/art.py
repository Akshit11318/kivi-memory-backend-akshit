"""ASCII plates for the lab. I/O only — no policy."""

from __future__ import annotations

from kivi_memory.cli.style import Ink
from kivi_memory.config import DEFAULT_PROFILE, DEFAULT_USER_ID, PROFILES


def banner(ink: Ink, profile: str = DEFAULT_PROFILE, user_id: str = DEFAULT_USER_ID) -> str:
    title = ink.bold("kivi")
    tag = ink.dim("spellings the model never met")
    spoken = " · ".join(ink.heard(w) for w in ("rustam", "meenakshi", "nilgiri"))
    written = " · ".join(ink.kept(w) for w in ("Rustom", "Meenakshi", "Nilgiri"))
    meta = ink.dim(f"{profile}  ·  {user_id}  ·  {', '.join(PROFILES)}")

    lines = [
        "",
        ink.rule(),
        f"  {title}    {tag}",
        ink.dim("  a small notebook for names, places, and pet words"),
        ink.rule(),
        f"  {ink.label('said')}      {spoken}",
        f"  {ink.label('written')}   {written}",
        ink.rule(),
        f"  {meta}",
        "",
    ]
    return "\n".join(lines)


def command_bench(ink: Ink) -> str:
    rows = [
        ("observe", "put a spelling in the notebook"),
        ("memories", "open what you have kept"),
        ("run", "try a new line — see if memory speaks"),
        ("eval", "score the notebook against fixtures"),
        ("reset", "clear the page  ·  --seed to refill"),
    ]
    out = ["", ink.label("  commands"), ""]
    for name, desc in rows:
        gap = " " * max(2, 12 - len(name))
        out.append(f"  {ink.bold(name)}{gap}{ink.dim(desc)}")
    out.append("")
    out.append(ink.dim('  kivi run --asr "…" --formatted "…"'))
    out.append("")
    return "\n".join(out)


def plate(ink: Ink, title: str, body: str, *, kind: str = "ink") -> str:
    paint = {
        "ink": ink.dim,
        "apply": ink.apply,
        "abstain": ink.abstain,
        "warn": ink.warn,
    }.get(kind, ink.dim)
    width = 56
    top = "┌" + "─" * (width - 2) + "┐"
    bot = "└" + "─" * (width - 2) + "┘"
    label = f" {title} "
    head = "┌" + label + "─" * max(1, width - 2 - len(label)) + "┐"
    lines = [paint(head if title else top)]
    for raw in body.splitlines() or [""]:
        clipped = raw[: width - 4]
        pad = " " * (width - 4 - len(clipped))
        lines.append(paint("│ ") + clipped + pad + paint(" │"))
    lines.append(paint(bot))
    return "\n".join(lines)


def error_line(ink: Ink, message: str) -> str:
    return plate(ink, "error", message, kind="warn")


def not_built(ink: Ink, command: str) -> str:
    return plate(
        ink,
        "later",
        f"{command} is not wired yet.\n"
        "the notebook skin is here; the engine lands in stages.\n"
        "see HANDOFF.md if you are implementing.",
        kind="warn",
    )


def trace_frame(
    ink: Ink,
    *,
    asr: str,
    formatted: str,
    decision: str,
    memory_aware: str,
    reason: str,
    profile: str,
) -> str:
    """Stable trace layout. Pipeline can call this once it exists."""
    flag = ink.apply("APPLY") if decision == "APPLY" else ink.abstain("ABSTAIN")
    parts = [
        ink.rule(),
        f"  {ink.label('run')}      {ink.bold(profile)}",
        ink.rule(),
        f"  {ink.label('said')}     {ink.heard(asr)}",
        f"  {ink.label('typed')}    {formatted}",
        f"  {ink.label('decide')}   {flag}",
        f"  {ink.label('written')}  {ink.kept(memory_aware)}",
        f"  {ink.label('why')}      {ink.dim(reason)}",
        ink.rule(),
    ]
    return "\n".join(parts)
