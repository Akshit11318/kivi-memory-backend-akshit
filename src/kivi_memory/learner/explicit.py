"""ExplicitLearner: dictionary_add and correction. plan.md: explicit only.

No unusual-word harvest, no ASR mining. Every write here is one of the two
named sources; the store never learns anything the learner didn't hand it.
"""

from __future__ import annotations

from dataclasses import dataclass

from kivi_memory.config import (
    CORRECTION_BUMP,
    DICTIONARY_ADD_CONFIDENCE,
    FIRST_CORRECTION_CONFIDENCE,
)
from kivi_memory.domain.models import Memory, Observation
from kivi_memory.learner.align import (
    content_window,
    diff_words,
    normalize_word,
    passes_grapheme_gate,
    strip_punct,
    tokenize_sentence,
)
from kivi_memory.store.db import MemoryStore, utc_now


@dataclass(frozen=True)
class CorrectionOutcome:
    """One word-diff candidate and whether the gate let it become a memory."""

    formatted_word: str
    final_word: str
    learned: bool
    reason: str
    memory: Memory | None = None


def _next_correction_confidence(existing: Memory | None, prior_corrections: int) -> float:
    """0.85 on first real correction (even over a seeded weak/below-threshold row,
    but never *below* an existing stronger row like a dictionary_add); +0.05 per
    later correction, capped at 1.0."""
    base = existing.confidence if existing else 0.0
    if prior_corrections == 0:
        return max(base, FIRST_CORRECTION_CONFIDENCE)
    return min(1.0, base + CORRECTION_BUMP)


def dictionary_add(
    store: MemoryStore, user_id: str, canonical: str, forms: list[str]
) -> Memory:
    """Strong observation. Confidence always 1.0. No sentence -> empty context_cues."""
    all_forms = {canonical.strip().lower(), *(f.strip().lower() for f in forms if f.strip())}
    memory = store.upsert_memory(
        user_id=user_id,
        canonical=canonical,
        forms=all_forms,
        confidence=DICTIONARY_ADD_CONFIDENCE,
        context_cues=(),
    )
    store.add_observation(
        Observation(
            user_id=user_id,
            source="dictionary_add",
            created_at=utc_now(),
            canonical=canonical,
            forms=tuple(forms),
            memory_id=memory.id,
        )
    )
    return memory


def correction(
    store: MemoryStore,
    user_id: str,
    formatted: str,
    final: str,
    asr: str | None = None,
) -> list[CorrectionOutcome]:
    """Word-align formatted vs final. Only pairs that pass the grapheme gate
    become memories. Optional `asr` is stored as evidence on the observation
    row, never mined for candidates."""
    formatted_tokens = tokenize_sentence(formatted)
    outcomes: list[CorrectionOutcome] = []

    for word_correction in diff_words(formatted, final):
        passed, reason = passes_grapheme_gate(
            word_correction.formatted_word, word_correction.final_word
        )
        if not passed:
            outcomes.append(
                CorrectionOutcome(
                    formatted_word=word_correction.formatted_word,
                    final_word=word_correction.final_word,
                    learned=False,
                    reason=reason,
                )
            )
            continue

        # strip_punct, not .strip(): a sentence-final word like "sandwich."
        # must not carry its period into the stored canonical, and the forms
        # must be normalized the same way retrieval will look them up.
        canonical = strip_punct(word_correction.final_word)
        observed_form = normalize_word(word_correction.formatted_word)
        canonical_form = normalize_word(canonical)
        cues = content_window(formatted_tokens, word_correction.index)

        existing = store.get_memory_by_canonical(user_id, canonical)
        prior_corrections = store.count_observations(user_id, canonical, "correction")
        confidence = _next_correction_confidence(existing, prior_corrections)

        memory = store.upsert_memory(
            user_id=user_id,
            canonical=canonical,
            forms={observed_form, canonical_form},
            confidence=confidence,
            context_cues=cues,
        )
        store.add_observation(
            Observation(
                user_id=user_id,
                source="correction",
                created_at=utc_now(),
                asr=asr,
                formatted=formatted,
                final=final,
                canonical=canonical,
                forms=(observed_form,),
                memory_id=memory.id,
            )
        )
        outcomes.append(
            CorrectionOutcome(
                formatted_word=word_correction.formatted_word,
                final_word=word_correction.final_word,
                learned=True,
                reason="ok",
                memory=memory,
            )
        )

    return outcomes


def replay(store: MemoryStore, entry: dict) -> Memory | list[CorrectionOutcome] | None:
    """Dispatch one `data/seed/observations.json` entry to the right learner call."""
    source = entry.get("source")
    user_id = entry.get("user_id", "demo")
    if source == "dictionary_add":
        return dictionary_add(store, user_id, entry["canonical"], entry.get("forms", []))
    if source == "correction":
        return correction(
            store,
            user_id,
            entry["formatted"],
            entry["final"],
            entry.get("asr"),
        )
    raise ValueError(f"unknown seed observation source: {source!r}")
