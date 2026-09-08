"""LLM sense helper — the last vote for a single surviving candidate.

Not a memory: it does not find names and it does not write SQLite. Given
exactly one candidate memory and the sentence a token appears in, it answers
REPLACE this token (APPLY) or ABSTAIN. No world knowledge beyond that one
sentence, and it is never called unless every cheap door in
decide/conservative.py already passed.

No cue fallback. Missing key, timeout, or an unparseable response all fall
through to the same ungated APPLY (helper="ungated") — see config.py and
README for why this is intentional, not a bug: without a key, a homograph
like Groww/grow or kiwi/Kivi WILL rewrite in every sentence.
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
    model_calls: int  # 0 (no key, never attempted) or 1 (a call was attempted)


def _build_prompt(sentence: str, token: str, memory: Memory) -> str:
    lines = [
        "You disambiguate ONE word in ONE sentence for a personal spelling notebook.",
        "A retrieval step already matched this token to the memory below (exact "
        "surface or phonetic similarity) -- do not re-judge whether the spelling is "
        "close enough, that part is decided. Your only job is SENSE: is this "
        "occurrence of the token being used to refer to the same "
        "person/place/product as the stored canonical, or something else?",
        "",
        f"Sentence: {sentence}",
        f"Token: {token}",
        f"Stored canonical: {memory.canonical}",
        f"Stored forms: {', '.join(memory.forms)}",
    ]
    if memory.teach_text:
        lines.append(f"Taught from: {memory.teach_text}")
    lines += [
        "",
        "APPLY if this token, in this sentence, is the same personal/product "
        "spelling as the stored canonical. ABSTAIN only when the sentence itself "
        "signals a different sense (its ordinary dictionary meaning, e.g. fruit vs "
        "brand, common word vs product), a different person, or a grammar/homophone "
        "issue. If nothing in the sentence suggests a different sense, APPLY. Use no "
        "world knowledge beyond this sentence.",
        "",
        'Reply with JSON only, no prose: {"decision": "APPLY"|"ABSTAIN", "reason": string}',
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


def _parse_decision(content: str) -> tuple[str, str]:
    """Parse `{"decision": ..., "reason": ...}`, tolerating a ```json fence."""
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    parsed = json.loads(text)
    decision = str(parsed["decision"]).strip().upper()
    if decision not in ("APPLY", "ABSTAIN"):
        raise ValueError(f"unexpected decision {decision!r}")
    reason = str(parsed.get("reason") or "").strip()
    return decision, reason


def decide_with_helper(sentence: str, token_core: str, memory: Memory) -> HelperResult:
    """The last vote for a single surviving candidate. Every cheap door in
    decide/conservative.py has already passed by the time this is called."""
    api_key = os.environ.get(LLM_API_KEY_ENV)
    if not api_key:
        return HelperResult("APPLY", _UNGATED_REASON, "ungated", None, 0.0, 0)

    model = os.environ.get(LLM_MODEL_ENV) or DEFAULT_LLM_MODEL
    base_url = os.environ.get(LLM_BASE_URL_ENV) or DEFAULT_LLM_BASE_URL
    prompt = _build_prompt(sentence, token_core, memory)

    start = time.perf_counter()
    try:
        content = _post_chat_completion(base_url, api_key, model, prompt)
        decision, reason = _parse_decision(content)
        latency_ms = (time.perf_counter() - start) * 1000
        if decision == "APPLY":
            return HelperResult("APPLY", reason or _LLM_APPLY_REASON, "llm", model, latency_ms, 1)
        return HelperResult(
            "ABSTAIN", reason or _LLM_ABSTAIN_DEFAULT_REASON, "llm", model, latency_ms, 1
        )
    except Exception:
        # Timeout, network error, non-2xx, or an unparseable response. No cue
        # fallback -- fall through to the same ungated APPLY as having no key.
        latency_ms = (time.perf_counter() - start) * 1000
        return HelperResult("APPLY", _UNGATED_REASON, "ungated", model, latency_ms, 1)
