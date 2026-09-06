"""Word-diff + grapheme gate + REFUSE_HOMOPHONE_PAIRS. plan.md pinned contracts #4, #8.

`there`/`their` (ratio 0.8) scores *higher* than `kiwi`/`kivi` (ratio 0.75) under
plain SequenceMatcher similarity — edit distance alone cannot tell a personal
spelling correction from a grammar fix. REFUSE_HOMOPHONE_PAIRS is the actual gate;
the ratio threshold only rejects genuinely unrelated words (Friday/Thursday).
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from difflib import SequenceMatcher

_STRIP_CHARS = string.punctuation + "“”‘’"

_GRAPHEME_RATIO_MIN = 0.6

REFUSE_HOMOPHONE_PAIRS: frozenset[frozenset[str]] = frozenset(
    frozenset(pair)
    for pair in (
        ("there", "their"),
        ("there", "they're"),
        ("their", "they're"),
        ("your", "you're"),
        ("its", "it's"),
        ("to", "too"),
        ("to", "two"),
        ("two", "too"),
        ("than", "then"),
        ("affect", "effect"),
        ("weather", "whether"),
        ("were", "we're"),
        ("who's", "whose"),
        ("here", "hear"),
    )
)

# Closed-class words: skipped when building context_cues windows (plan.md #8),
# and a same-both-sides veto in the grapheme gate (plan.md #4 rule 4).
COMMON_FUNCTION_WORDS: frozenset[str] = frozenset(
    """
    the a an to of and or but for on in at is was were be been being
    this that these those he she it they we you i as if so nor not
    do does did have has had will would can could should shall may
    might must with from by about into onto over under again further
    then there here when where why how all any both each few more
    most other some such no yes only own same than too very s t
    me my mine us our ours him her hers them their theirs
    """.split()
)

STOPLIST = COMMON_FUNCTION_WORDS


def strip_punct(token: str) -> str:
    return token.strip(_STRIP_CHARS)


def normalize_word(token: str) -> str:
    return strip_punct(token).lower()


def tokenize_sentence(text: str) -> list[str]:
    return text.split()


@dataclass(frozen=True)
class WordCorrection:
    """One aligned (formatted, final) word pair from an equal-length replace span."""

    index: int
    formatted_word: str
    final_word: str


def diff_words(formatted: str, final: str) -> list[WordCorrection]:
    """Word-align formatted vs final. Only 1:1 equal-length replace spans are candidates.

    Inserts/deletes/unequal-length replaces are structural sentence edits, not a
    personal-vocabulary correction — they are not candidates at all.
    """
    formatted_tokens = tokenize_sentence(formatted)
    final_tokens = tokenize_sentence(final)
    formatted_norm = [normalize_word(t) for t in formatted_tokens]
    final_norm = [normalize_word(t) for t in final_tokens]

    matcher = SequenceMatcher(a=formatted_norm, b=final_norm, autojunk=False)
    corrections: list[WordCorrection] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "replace" or (i2 - i1) != (j2 - j1):
            continue
        for offset in range(i2 - i1):
            corrections.append(
                WordCorrection(
                    index=i1 + offset,
                    formatted_word=formatted_tokens[i1 + offset],
                    final_word=final_tokens[j1 + offset],
                )
            )
    return corrections


def is_refused_homophone(norm_a: str, norm_b: str) -> bool:
    return frozenset({norm_a, norm_b}) in REFUSE_HOMOPHONE_PAIRS


def is_grapheme_similar(norm_a: str, norm_b: str) -> bool:
    if not norm_a or not norm_b or norm_a[0] != norm_b[0]:
        return False
    return SequenceMatcher(None, norm_a, norm_b).ratio() >= _GRAPHEME_RATIO_MIN


def passes_grapheme_gate(formatted_word: str, final_word: str) -> tuple[bool, str]:
    """All four gate rules from plan.md pinned contract #4. Returns (passed, reason)."""
    raw_formatted, raw_final = strip_punct(formatted_word), strip_punct(final_word)
    norm_formatted, norm_final = raw_formatted.lower(), raw_final.lower()

    if not norm_formatted or not norm_final:
        return False, "empty_token"
    if raw_formatted != raw_final and norm_formatted == norm_final:
        return False, "case_only"
    if norm_formatted == norm_final:
        return False, "no_change"
    if is_refused_homophone(norm_formatted, norm_final):
        return False, "refused_homophone"
    if norm_formatted in COMMON_FUNCTION_WORDS and norm_final in COMMON_FUNCTION_WORDS:
        return False, "both_function_words"
    if not is_grapheme_similar(norm_formatted, norm_final):
        return False, "not_grapheme_similar"
    return True, "ok"


def content_window(tokens: list[str], index: int, radius: int = 2) -> set[str]:
    """±radius normalized content tokens around index, skipping the stoplist.

    Walks outward past stoplist tokens so the window always tries to reach
    `radius` real content words rather than counting stopwords against it.
    """
    normalized = [normalize_word(t) for t in tokens]
    cues: set[str] = set()

    i, taken = index - 1, 0
    while i >= 0 and taken < radius:
        tok = normalized[i]
        if tok and tok not in STOPLIST:
            cues.add(tok)
            taken += 1
        i -= 1

    i, taken = index + 1, 0
    while i < len(normalized) and taken < radius:
        tok = normalized[i]
        if tok and tok not in STOPLIST:
            cues.add(tok)
            taken += 1
        i += 1

    return cues
