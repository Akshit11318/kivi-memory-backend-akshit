"""Per-token APPLY iff confidence >= 0.75, unique canonical, disagrees, and
(if the memory cleared MIN_CUES_FOR_GATE) the sentence window overlaps them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from kivi_memory.config import APPLY_THRESHOLD, MIN_CUES_FOR_GATE
from kivi_memory.domain.models import Memory


@dataclass(frozen=True)
class DecideResult:
    decision: str  # "APPLY" | "ABSTAIN"
    reason: str
    memory: Memory | None = None


def decide_token(
    token_core: str, candidates: list[Memory], context_window: Iterable[str]
) -> DecideResult:
    if not candidates:
        return DecideResult("ABSTAIN", "no_memory")

    canonicals = {m.canonical for m in candidates}
    if len(canonicals) > 1:
        return DecideResult("ABSTAIN", "conflicting_canonicals")

    memory = candidates[0]

    if memory.confidence < APPLY_THRESHOLD:
        return DecideResult("ABSTAIN", "low_confidence")

    # Case is not a correction signal (family 20): a token that already spells
    # the canonical, modulo case, needs no rewrite.
    if token_core.lower() == memory.canonical.lower():
        return DecideResult("ABSTAIN", "already_canonical")

    if len(memory.context_cues) >= MIN_CUES_FOR_GATE and not (
        set(memory.context_cues) & set(context_window)
    ):
        return DecideResult("ABSTAIN", "context_mismatch")

    return DecideResult("APPLY", "ok", memory)
