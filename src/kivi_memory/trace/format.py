"""Builds the inspectable run record. plan.md: trace.

Pretty traces use the CLI plate so the lab looks the same everywhere. JSON
traces are the full record: ASR, formatted, per-token decisions, reasons,
memories used, profile, latency — everything `RunTrace` carries.
"""

from __future__ import annotations

from dataclasses import asdict

from kivi_memory.cli.art import trace_frame
from kivi_memory.cli.style import Ink, color_enabled
from kivi_memory.domain.models import RunTrace

__all__ = ["Ink", "color_enabled", "trace_frame", "trace_to_dict"]


def trace_to_dict(trace: RunTrace) -> dict:
    return asdict(trace)


def overall_decision(trace: RunTrace) -> tuple[str, str]:
    """Collapse per-token decisions into one (decision, reason) pair for a
    one-line summary. `off` never runs decide at all, so it's a fixed pair."""
    if trace.profile == "off":
        return "ABSTAIN", "memory disabled"

    applied = [d for d in trace.decisions if d.decision == "APPLY"]
    if applied:
        canonicals = sorted({d.canonical for d in applied if d.canonical})
        return "APPLY", "applied " + ", ".join(canonicals)

    reasons = sorted({d.reason for d in trace.decisions}) or ["no_memory"]
    return "ABSTAIN", ", ".join(reasons)
