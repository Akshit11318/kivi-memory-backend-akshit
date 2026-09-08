"""Cheap doors, first no wins. No cue gate, no context window — sense
disambiguation for a surviving single candidate is the LLM helper's job
(decide/llm_helper.py), not this module's.

Order: no candidates -> conflicting canonicals -> low confidence -> already
canonical. Any of these is a definitive ABSTAIN. If none fire, this returns
a pending result (decision=None) carrying the single surviving memory —
the caller hands that to the LLM helper (or, with no key, ungated APPLY).
"""

from __future__ import annotations

from dataclasses import dataclass

from kivi_memory.config import APPLY_THRESHOLD
from kivi_memory.domain.models import Memory


@dataclass(frozen=True)
class GateResult:
    decision: str | None  # "ABSTAIN", or None meaning "no cheap door closed"
    reason: str | None
    memory: Memory | None = None


def cheap_gate(token_core: str, candidates: list[Memory]) -> GateResult:
    if not candidates:
        return GateResult("ABSTAIN", "no_memory")

    canonicals = {m.canonical for m in candidates}
    if len(canonicals) > 1:
        return GateResult("ABSTAIN", "conflicting_canonicals")

    memory = candidates[0]

    if memory.confidence < APPLY_THRESHOLD:
        return GateResult("ABSTAIN", "low_confidence")

    # Case is not a correction signal: a token that already spells the
    # canonical, modulo case, needs no rewrite.
    if token_core.lower() == memory.canonical.lower():
        return GateResult("ABSTAIN", "already_canonical")

    return GateResult(None, None, memory)
