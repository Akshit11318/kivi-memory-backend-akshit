"""LLM sense helper — the last vote for a single surviving memory.

Not a memory: it does not find names and it does not write SQLite. Given
one candidate memory and every occurrence of its token in one sentence
(marked and numbered — see pipeline.align.mark_occurrences), it scores
0-100 per occurrence how confident it is that occurrence is the same sense
as the stored canonical. One call per (memory, sentence), not one call per
occurrence: "one sense per discourse" (Gale/Church/Yarowsky) is a real
pattern — a repeated word usually keeps its sense — but it's a hypothesis
the model verifies per occurrence in one pass, not an assumption we make
for it. A genuine intra-sentence sense switch ("moved funds from grow as
profits didnt grow") still gets two different scores from the one call.

Each score is blended with the memory's own confidence — the score alone
can't tell a shaky respelling from a rock-solid one, and the memory's
confidence alone can't tell sense — so neither signal decides alone:

    combined = memory.confidence * (score / 100)
    APPLY iff combined >= LLM_COMBINED_APPLY_THRESHOLD, else ABSTAIN

It is never called unless every cheap door in decide/conservative.py already
passed. No cue fallback: missing key, timeout, or an unparseable/malformed
response all fall through to the same ungated APPLY for every occurrence in
the batch (helper="ungated") — see config.py and README for why this is
intentional, not a bug: without a key, a homograph like Groww/grow or
kiwi/Kivi WILL rewrite in every sentence.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass

from kivi_memory.config import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    LLM_API_KEY_ENV,
    LLM_BASE_URL_ENV,
    LLM_COMBINED_APPLY_THRESHOLD,
    LLM_MODEL_ENV,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)
from kivi_memory.domain.models import Memory

_UNGATED_REASON = "ungated"
_LLM_APPLY_REASON = "llm_ok"
_LLM_ABSTAIN_DEFAULT_REASON = "sense_mismatch"


@dataclass(frozen=True)
class HelperResult:
    decision: str  # "APPLY" | "ABSTAIN"
    reason: str
    helper: str  # "llm" | "ungated"
    model: str | None
    latency_ms: float
    model_calls: int  # 1 on exactly one HelperResult per batch, 0 on the rest
    score: float | None = None  # raw 0-100 LLM sense score; None when helper == "ungated"


def _build_prompt(marked_sentence: str, token: str, memory: Memory, count: int) -> str:
    lines = [
        f"You score {count} occurrence(s) of the same word in one sentence for a "
        "personal spelling notebook.",
        "Each occurrence to judge is wrapped and numbered: [[#1: word]], [[#2: word]], "
        "etc. Score every occurrence independently -- a repeated word usually keeps the "
        "same sense throughout a sentence, but it can switch partway through. Do not "
        "assume they all match just because they're the same word; verify each one "
        "against its own local context.",
        "A retrieval step already matched this token to the memory below (exact surface "
        "or phonetic similarity) -- do not re-judge whether the spelling is close enough, "
        "that part is decided. Your only job is SENSE, per occurrence.",
        "",
        f"Sentence: {marked_sentence}",
        f"Token: {token}",
        f"Stored canonical: {memory.canonical}",
        f"Stored forms: {', '.join(memory.forms)}",
    ]
    if memory.teach_text:
        lines.append(f"Taught from: {memory.teach_text}")
    lines += [
        "",
        "For each occurrence, score 0-100 how confident you are that it is the same "
        "personal/product spelling as the stored canonical, used in the same sense. "
        "100 = certainly the same sense. 0 = certainly a different sense (its ordinary "
        "dictionary meaning, e.g. fruit vs brand, common word vs product), a different "
        "person, or a grammar/homophone issue. Use no world knowledge beyond this "
        "sentence.",
        "",
        'Reply with JSON only, no prose: {"occurrences": '
        '[{"occurrence": <1-based int>, "score": <integer 0-100>, "reason": string}, ...]}'
        f" with exactly {count} item(s), one per occurrence number, in any order.",
    ]
    return "\n".join(lines)


def _post_chat_completion(base_url: str, api_key: str, model: str, prompt: str) -> str:
    """One OpenAI-compatible chat completion call. Returns the assistant's raw
    text content. Isolated here so tests mock this one seam instead of urllib,
    and so the eval CSV runner never needs its own HTTP client."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "temperature": LLM_TEMPERATURE,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Some OpenAI-compatible hosts (e.g. Groq, behind Cloudflare) 403
            # Python's default "Python-urllib/x.y" user agent as a bot signature.
            "User-Agent": "kivi-memory/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def _parse_batch(content: str, count: int) -> list[tuple[float, str]]:
    """Parse `{"occurrences": [{"occurrence": N, "score": ..., "reason": ...}, ...]}`,
    tolerating a ```json fence. Returns scores/reasons ordered 1..count.
    Raises if the count doesn't match or an occurrence number is missing --
    the caller treats that the same as any other malformed response."""
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    parsed = json.loads(text)
    items = parsed["occurrences"]
    if len(items) != count:
        raise ValueError(f"expected {count} occurrences, got {len(items)}")

    by_order: dict[int, tuple[float, str]] = {}
    for item in items:
        order = int(item["occurrence"])
        score = max(0.0, min(100.0, float(item["score"])))
        reason = str(item.get("reason") or "").strip()
        by_order[order] = (score, reason)
    return [by_order[i] for i in range(1, count + 1)]


def decide_with_helper(
    marked_sentence: str, token_core: str, memory: Memory, count: int
) -> list[HelperResult]:
    """The last vote for one memory's `count` occurrence(s) in one sentence,
    scored together in a single call. Every cheap door in
    decide/conservative.py has already passed for each occurrence by the
    time this is called. `marked_sentence` has every occurrence numbered
    `[[#N: ...]]` (see pipeline.align.mark_occurrences). Returns exactly
    `count` results, ordered 1..count."""
    api_key = os.environ.get(LLM_API_KEY_ENV)
    if not api_key:
        return [HelperResult("APPLY", _UNGATED_REASON, "ungated", None, 0.0, 0) for _ in range(count)]

    model = os.environ.get(LLM_MODEL_ENV) or DEFAULT_LLM_MODEL
    base_url = os.environ.get(LLM_BASE_URL_ENV) or DEFAULT_LLM_BASE_URL
    prompt = _build_prompt(marked_sentence, token_core, memory, count)

    start = time.perf_counter()
    try:
        content = _post_chat_completion(base_url, api_key, model, prompt)
        scored = _parse_batch(content, count)
        latency_ms = (time.perf_counter() - start) * 1000
        results = []
        for i, (score, reason) in enumerate(scored):
            combined = memory.confidence * (score / 100.0)
            model_calls = 1 if i == 0 else 0  # one HTTP call total for the whole batch
            if combined >= LLM_COMBINED_APPLY_THRESHOLD:
                results.append(
                    HelperResult(
                        "APPLY", reason or _LLM_APPLY_REASON, "llm", model, latency_ms, model_calls, score
                    )
                )
            else:
                results.append(
                    HelperResult(
                        "ABSTAIN",
                        reason or _LLM_ABSTAIN_DEFAULT_REASON,
                        "llm",
                        model,
                        latency_ms,
                        model_calls,
                        score,
                    )
                )
        return results
    except Exception:
        # Timeout, network error, non-2xx, or a malformed/mismatched-count
        # response. No cue fallback -- fall through to the same ungated
        # APPLY, for every occurrence in the batch, as having no key.
        latency_ms = (time.perf_counter() - start) * 1000
        return [
            HelperResult("APPLY", _UNGATED_REASON, "ungated", model, latency_ms, 1 if i == 0 else 0)
            for i in range(count)
        ]
