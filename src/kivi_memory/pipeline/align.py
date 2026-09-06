"""SequenceMatcher ASR<->formatted. Never positional 1:1. plan.md pinned contracts #1, #5.

Decide only runs on formatted tokens; alignment's job is to hand decide extra
candidate surfaces from the ASR side of a matched span. A formatter-only
insertion (no aligned ASR span) still gets checked on its own surface — it
just gets nothing extra from the ASR side.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from kivi_memory.learner.align import normalize_word

_LEADING_CHARS = "\"'“‘([{"
_TRAILING_CHARS = "\"'”’)]}.,;:!?"
_POSSESSIVE_SUFFIXES = ("'s", "’s")


@dataclass(frozen=True)
class DecomposedToken:
    """A whitespace-split token, split into parts that stitch back losslessly:
    `raw == prefix + core + possessive + suffix`.
    """

    raw: str
    prefix: str
    core: str
    possessive: str
    suffix: str


def decompose_token(raw: str) -> DecomposedToken:
    prefix = ""
    rest = raw
    while rest and rest[0] in _LEADING_CHARS:
        prefix += rest[0]
        rest = rest[1:]

    suffix = ""
    while rest and rest[-1] in _TRAILING_CHARS:
        suffix = rest[-1] + suffix
        rest = rest[:-1]

    possessive = ""
    for suf in _POSSESSIVE_SUFFIXES:
        if rest.lower().endswith(suf) and len(rest) > len(suf):
            possessive = rest[-len(suf) :]
            rest = rest[: -len(suf)]
            break

    return DecomposedToken(raw=raw, prefix=prefix, core=rest, possessive=possessive, suffix=suffix)


def tokenize(text: str) -> list[DecomposedToken]:
    return [decompose_token(word) for word in text.split()]


def match_keys(token: DecomposedToken) -> list[str]:
    """Normalized candidate surfaces for this token: the whole core, and (for a
    hyphenated core) each segment — `Sarvam-Kivi` checks as itself and as
    `sarvam` / `kivi` (plan.md #5)."""
    core_norm = normalize_word(token.core)
    if not core_norm:
        return []
    keys = [core_norm]
    if "-" in token.core:
        keys.extend(seg for seg in (normalize_word(s) for s in token.core.split("-")) if seg)
    return keys


def align_formatted_to_asr(asr_tokens_norm: list[str], formatted_core_norm: list[str]) -> dict[int, list[int]]:
    """Map each formatted index to the ASR indices in its aligned span.

    Only 'equal' and 'replace' opcodes contribute — a pure formatter insertion
    (no ASR counterpart) maps to an empty list, never to a neighboring index.
    Equal-length spans (the common case, including whole-sentence 'equal')
    map position-by-position; only a genuinely uneven `replace` (e.g. `gonna`
    -> `going to`) falls back to handing every token in the span the whole
    opposite span, since there's no 1:1 correspondence to assert there.
    """
    matcher = SequenceMatcher(a=asr_tokens_norm, b=formatted_core_norm, autojunk=False)
    mapping: dict[int, list[int]] = {j: [] for j in range(len(formatted_core_norm))}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag not in ("equal", "replace"):
            continue
        if (i2 - i1) == (j2 - j1):
            for offset in range(j2 - j1):
                mapping[j1 + offset] = [i1 + offset]
        else:
            asr_span = list(range(i1, i2))
            for j in range(j1, j2):
                mapping[j] = asr_span
    return mapping


def stitch(tokens: list[DecomposedToken], cores: list[str]) -> str:
    return " ".join(tok.prefix + core + tok.possessive + tok.suffix for tok, core in zip(tokens, cores))
