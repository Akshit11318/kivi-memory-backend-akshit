"""LLM sense helper — last vote for every surviving token in one sentence.

Not a memory: it does not find names and does not write SQLite. Retrieval and
the cheap doors have already run. Whatever is still pending in this sentence
is scored in **one** HTTP call (all memories, all repeats), not one call per
memory. Repeats of the same word keep independent scores via [[#N: ...]]
markers (see pipeline.align.mark_occurrences).

Each score is blended with that occurrence's memory confidence:

    combined = memory.confidence * (score / 100)
    APPLY iff combined >= LLM_COMBINED_APPLY_THRESHOLD, else ABSTAIN

`--decide llm` (default) requires KIVI_LLM_API_KEY and KIVI_LLM_MODEL.
Timeout or a malformed response → ABSTAIN llm_unavailable, not a silent
rewrite. `--decide ungated` skips the HTTP call (latency ablation).
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass

from kivi_memory.config import (
    LLM_COMBINED_APPLY_THRESHOLD,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    llm_credentials,
)
from kivi_memory.domain.models import Memory

_UNGATED_REASON = "ungated"
_UNAVAILABLE_REASON = "llm_unavailable"
_LLM_APPLY_REASON = "llm_ok"
_LLM_ABSTAIN_DEFAULT_REASON = "sense_mismatch"


@dataclass(frozen=True)
class HelperResult:
    decision: str  # "APPLY" | "ABSTAIN"
    reason: str
    helper: str  # "llm" | "ungated"
    model: str | None
    latency_ms: float
    model_calls: int  # 1 on exactly one HelperResult per sentence call, 0 on the rest
    score: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


def _build_prompt(marked_sentence: str, items: list[tuple[str, Memory]]) -> str:
    count = len(items)
    lines = [
        f"You score {count} marked occurrence(s) in one sentence for a personal spelling notebook.",
        "Each occurrence is wrapped and numbered: [[#1: word]], [[#2: word]], etc.",
        "They may be different words and different stored memories. Score each number "
        "independently against ITS OWN stored canonical. A repeated word can switch sense "
        "partway through; do not assume all marks of the same spelling share a verdict.",
        "Retrieval already matched spelling. Do not re-judge edit distance. Your only job "
        "is SENSE, per occurrence.",
        "",
        f"Sentence: {marked_sentence}",
        "",
        "Memories, one per occurrence number:",
    ]
    for i, (token, memory) in enumerate(items, start=1):
        lines.append(f"#{i} token={token!r} canonical={memory.canonical!r} forms={list(memory.forms)}")
        if memory.teach_text:
            lines.append(f"    taught from: {memory.teach_text}")
    lines += [
        "",
        "For each occurrence, score 0-100 how confident you are that it is the same "
        "personal/product spelling as THAT occurrence's stored canonical, in the same sense. "
        "100 = certainly the same sense. 0 = certainly a different sense (ordinary dictionary "
        "meaning, fruit vs brand, common word vs product), a different person, or grammar. "
        "Use no world knowledge beyond this sentence.",
        "",
        'Reply with JSON only, no prose: {"occurrences": '
        '[{"occurrence": <1-based int>, "score": <integer 0-100>, "reason": string}, ...]}'
        f" with exactly {count} item(s), one per occurrence number.",
    ]
    return "\n".join(lines)


def _completions_url(base_url: str) -> str:
    """OpenAI-compatible hosts want .../v1 + /chat/completions.

    If the env already includes /chat/completions (a common copy-paste from
    curl docs), do not append it again.
    """
    url = base_url.rstrip("/")
    if url.endswith("/chat/completions"):
        return url
    return url + "/chat/completions"


def _post_chat_completion(base_url: str, api_key: str, model: str, prompt: str) -> tuple[str, dict]:
    """One OpenAI-compatible chat completion call. Returns assistant text and usage."""
    body = {
        "model": model,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    # GLM-5.3-flash is thinking-only (cannot disable). Older GLM accepts
    # reasoning_effort=none so it does not spend seconds on a hidden chain.
    if "glm-5p3" not in model.lower():
        body["reasoning_effort"] = "none"
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        _completions_url(base_url),
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "kivi-memory/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=LLM_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"], body.get("usage") or {}


def _parse_batch(content: str, count: int) -> list[tuple[float, str]]:
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


def _ungated(count: int) -> list[HelperResult]:
    return [
        HelperResult("APPLY", _UNGATED_REASON, "ungated", None, 0.0, 0) for _ in range(count)
    ]


def _unavailable(
    count: int, model: str | None, latency_ms: float, attempted: bool
) -> list[HelperResult]:
    return [
        HelperResult(
            "ABSTAIN",
            _UNAVAILABLE_REASON,
            "llm",
            model,
            latency_ms,
            1 if attempted and i == 0 else 0,
        )
        for i in range(count)
    ]


def decide_sentence(
    marked_sentence: str,
    items: list[tuple[str, Memory]],
    decide: str = "llm",
) -> list[HelperResult]:
    """Score every pending occurrence in this sentence in one call.

    `items[i]` is occurrence i+1 (token_core, memory). Returns len(items) results.
    `decide="ungated"` skips the model (latency path). `decide="llm"` requires
    key + model; a missing config, timeout, or bad JSON ABSTAINs.
    """
    count = len(items)
    if count == 0:
        return []

    if decide == "ungated":
        return _ungated(count)

    creds = llm_credentials()
    if creds is None:
        return _unavailable(count, None, 0.0, attempted=False)

    api_key, base_url, model = creds
    prompt = _build_prompt(marked_sentence, items)

    start = time.perf_counter()
    try:
        content, usage = _post_chat_completion(base_url, api_key, model, prompt)
        scored = _parse_batch(content, count)
        latency_ms = (time.perf_counter() - start) * 1000
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        results = []
        for i, ((token, memory), (score, reason)) in enumerate(zip(items, scored)):
            del token  # listed in the prompt; blend uses this occurrence's memory
            combined = memory.confidence * (score / 100.0)
            decision = "APPLY" if combined >= LLM_COMBINED_APPLY_THRESHOLD else "ABSTAIN"
            default_reason = _LLM_APPLY_REASON if decision == "APPLY" else _LLM_ABSTAIN_DEFAULT_REASON
            results.append(
                HelperResult(
                    decision,
                    reason or default_reason,
                    "llm",
                    model,
                    latency_ms,
                    1 if i == 0 else 0,
                    score,
                    prompt_tokens if i == 0 else None,
                    completion_tokens if i == 0 else None,
                )
            )
        return results
    except Exception:
        latency_ms = (time.perf_counter() - start) * 1000
        return _unavailable(count, model, latency_ms, attempted=True)
