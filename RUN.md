Completely local application. Python 3.13+ via uv. SQLite file on disk.
`--decide llm` (default) **requires** `KIVI_LLM_API_KEY` and `KIVI_LLM_MODEL`.
`--decide ungated` skips the model so you can measure retrieve latency.
No hosted URL.

## 1. Runtimes

- Python 3.13+
- uv 0.4+

## 2. Environment variables

**Compulsory for `--decide llm`** (the default on `kivi run` and `kivi eval`).
Copy `.env.example` to `.env` and fill **both** key and model. Empty values
count as unset — the CLI errors rather than silently rewriting.

**Do not set a thinking / reasoning-only model** (GLM-5.3-flash, `glm-5p3`,
or any id that cannot disable thinking). Those burn the timeout on a hidden
chain and often return empty JSON, so every last vote becomes
`llm_unavailable`. Use a normal instruct or Fast path
(`accounts/fireworks/routers/glm-5p2-fast`, or Haiku).

For retrieve-only latency, pass `--decide ungated` (no env needed).

| Variable            | Default                                            | Purpose                                  |
| -------------------- | --------------------------------------------------- | ------------------------------------------ |
| `KIVI_LLM_API_KEY`    | **required** for `--decide llm`                      | last vote for APPLY vs ABSTAIN           |
| `KIVI_LLM_BASE_URL`   | `https://api.anthropic.com/v1`                       | OpenAI-compatible chat completions host  |
| `KIVI_LLM_MODEL`      | **required** for `--decide llm` (example: `claude-haiku-4-5-20251001`) | model id |

Default provider is Anthropic (`console.anthropic.com`), via its
OpenAI-compatible endpoint — no Anthropic SDK, no provider-specific code,
same `_post_chat_completion` as every other host. `decide/llm_helper.py`
has zero Anthropic-specific code — just point `KIVI_LLM_BASE_URL` /
`KIVI_LLM_MODEL` elsewhere for a different provider, e.g. free-tier Groq:

```
KIVI_LLM_BASE_URL=https://api.groq.com/openai/v1
KIVI_LLM_MODEL=openai/gpt-oss-20b
```

**Why Haiku over a free model.** Measured against the same scenarios
(fruit vs brand, zero-shared-vocabulary sense checks, and the hardest case
— the same word twice with two different senses in one sentence), on real
live calls:

| Provider / model                          | Cost | Required scenarios | Hard same-sentence case |
| ------------------------------------------- | ---- | ------------------- | ------------------------- |
| Anthropic `claude-haiku-4-5-20251001`       | paid | 7/7                 | correct, both occurrences  |
| Groq `openai/gpt-oss-20b`                   | free | 4/4                 | 1 of 2 occurrences correct |
| Groq `openai/gpt-oss-120b`                  | free | 4/4                 | same miss as 20b, 6x the size |
| Groq `qwen/qwen3.8-27b`                     | free | 2/4                 | correct                    |
| OpenRouter free tier (various)              | free | slug/quality churn — see git history for the deprecations we hit | not reliably tested |

If you don't have an Anthropic key, Groq is a real free option, just a
lower-accuracy one on genuinely ambiguous cases — the required scenarios
still pass.

Copy `.env.example` to `.env` and fill **key and model**. Never commit a
real key. `config.py` auto-loads `.env` on startup (it never overrides a
real `export`):

```
cp .env.example .env
# edit .env, set KIVI_LLM_API_KEY and KIVI_LLM_MODEL
```

## 3. Install

```
uv sync
```

## 4. Create, migrate, and seed

The SQLite file is created and migrated on first open.

```
uv run kivi reset --seed
```

This wipes `data/kivi.sqlite` (created if missing) and replays
`data/seed/observations.json`.

```
uv run kivi memories
```

You should see seeded lexical rows (the brief pair plus dictionary
adds such as vLLM, Priyaa, …). After a plain `reset` with no
`--seed`, this list is empty `[]`.

## 5. Start

No daemon. The CLI is the process:

```
uv run kivi
```

or

```
uv run kivi --help
```

## 6. Interface

Terminal. No URL. The CLI prints the notebook skin. Set `NO_COLOR=1` if you want it off.

## 7. Primary interactions

Wipe first so you are not mixing this with seed leftovers:

```
uv run kivi reset
```

**Teach** from one correction. ASR heard `akshith` / `postgress` /
`graffana`. The user writes `Akshit`, `Postgres`, `Grafana`.

```
uv run kivi observe --source correction \
  --asr "ask akshith to bump postgress and graffana" \
  --formatted "Ask Akshith to bump postgress and graffana." \
  --final "Ask Akshit to bump Postgres and Grafana."
```

Expect three `learned: true` rows at confidence 0.85.

**Inspect** the notebook:

```
uv run kivi memories
```

Expect `Akshit` (form `akshith`), `Postgres` (`postgress`), `Grafana`
(`graffana`).

**Run** a *new* line (same terms, different sentence). Use
`--decide ungated` so this step does not need a model key. Expected:
APPLY on all three, written
`Ping Akshit after the Postgres and Grafana deploy.`

```
uv run kivi --decide ungated run \
  --asr "ping akshith after the postgress and graffana deploy" \
  --formatted "Ping Akshith after the postgress and graffana deploy."
```

**Deliberate no-op** (nothing in the notebook matches). Expected:
ABSTAIN, formatted unchanged, `no_memory`.

```
uv run kivi --decide ungated run \
  --asr "ship the invoice on friday" \
  --formatted "Ship the invoice on Friday."
```

**Control:** `--profile off` must equal formatted on the Akshit line.

```
uv run kivi --profile off run \
  --asr "ping akshith after the postgress and graffana deploy" \
  --formatted "Ping Akshith after the postgress and graffana deploy."
```

**Reset** and repeat the same journey.

Optional dictionary teach (`--context` stores an example sentence as
`teach_text` — evidence for the LLM sense helper's prompt, not a gate):

```
uv run kivi observe --source dictionary_add --canonical Terraform --forms terrafrom
uv run kivi observe --source dictionary_add --canonical Groww --forms grow --context "I moved my SIP to Groww."
```

`run --json` prints the full inspectable trace, including `matched_via`
(`exact` | `phonetic` | `null`), `decide` (`llm` | `ungated` | `off`),
`helper` (`llm` | `ungated` | `null`), and
`llm_score` (the raw 0-100 sense score the LLM returned, only set when
`helper == "llm"`) per token. `prompt_tokens`/`completion_tokens` appear on
both the token that made the real HTTP call (the first in its batch) and
the top-level trace (summed across the whole run) — useful for estimating
real API cost; see `scripts/stress_test/` for a worked example.

### 7.1 Demos that run with `--decide ungated` (latency path)

All of these use the live store `data/kivi.sqlite` (created on first
open). Do not pass `--db`. Start each block with `uv run kivi reset` so
leftover rows from the last demo do not leak in. `--decide ungated` skips
the model so you can see retrieve + cheap-door latency.

**A. Alignment, not position — the Akshit paragraph.** The formatter turned
4 ASR tokens into 5 (`im gonna` → `I'm going to`). A positional
`token[i] → token[i]` system corrupts `I'm`. This one rewrites only the
target, across three different names in one line.

```
uv run kivi reset
uv run kivi observe --source correction \
  --asr "ask akshith to bump postgress and graffana" \
  --formatted "Ask Akshith to bump postgress and graffana." \
  --final "Ask Akshit to bump Postgres and Grafana."
uv run kivi --decide ungated run --asr "im gonna ask akshith" --formatted "I'm going to ask Akshith."
```

Expected: APPLY, written `I'm going to ask Akshit.`

**B. `exact` vs `auto` — the graffana paragraph.** `Grafana` is stored with
no `graffana` form. `exact` cannot find it; `auto` falls through to the
phonetic retriever in the same cascade.

```
uv run kivi reset
uv run kivi observe --source dictionary_add --canonical Grafana --forms grafana
uv run kivi --profile exact --decide ungated run --formatted "Please restart the graffana pod."
uv run kivi --profile auto --decide ungated run --formatted "Please restart the graffana pod."
```

Expected: `exact` ABSTAIN `no_memory` (formatted unchanged); `auto` APPLY,
written `Please restart the Grafana pod.` (`matched_via: "phonetic"` in
`--json`).

**C. The learner refusing to learn.** A content edit and a grammar
homophone both look like small spelling fixes to edit distance.
Neither writes a row.

```
uv run kivi reset
uv run kivi observe --source correction \
  --formatted "Ship it on Friday." \
  --final "Ship it on Thursday."
uv run kivi observe --source correction \
  --formatted "Send it to there team." \
  --final "Send it to their team."
uv run kivi memories
```

Expected: both observes `learned: false` (`not_grapheme_similar`,
`refused_homophone`). `memories` is `[]`.

**D. Two real people, one surface — and the full trace.** Both rows
match `Ria`, they disagree, so the token is refused and both memory
ids are named in the trace.

```
uv run kivi reset
uv run kivi observe --source dictionary_add --canonical Riya --forms ria
uv run kivi observe --source dictionary_add --canonical Ria --forms riya
uv run kivi --decide ungated run --formatted "Ria sent the deck." --json
```

In the JSON, the `Ria` token is ABSTAIN `conflicting_canonicals` with
`memory_ids` listing both rows, `helper: null` — the LLM is never called
once a cheap door has already closed.

**E. `--decide ungated`, documented: a homograph rewrites everywhere.**
Without a sense check, `kiwi`/`Kivi` rewrites the grocery sentence too,
not just the work one.

```
uv run kivi reset
uv run kivi observe --source correction \
  --formatted "Please review the Sarvam Kiwi rollout." \
  --final "Please review the Sarvam Kivi rollout."
uv run kivi --decide ungated run --formatted "Remind me to buy kiwi tomorrow."
```

Expected: APPLY, written `Remind me to buy Kivi tomorrow.` (`helper:
"ungated"` in `--json`). This is the latency path, not a bug — see README
"LLM sense helper".

### 7.2 Demos that need `--decide llm` (key + model compulsory)

Set a real key and model first (§2). These show the sense check §7.1E
documents the absence of. `kivi run` defaults to `--decide llm`.

**F. Fruit vs brand.** Same `Kivi` memory as demo E. With a key, the
grocery sentence now correctly ABSTAINs.

```
uv run kivi reset
uv run kivi observe --source correction \
  --formatted "Please review the Sarvam Kiwi rollout." \
  --final "Please review the Sarvam Kivi rollout."
uv run kivi run --formatted "Buy kiwi at the store this weekend if the fruit looks good."
uv run kivi run --formatted "Restart the Kiwi pod in staging before the client demo tomorrow."
```

Expected: the grocery line ABSTAINs (`helper: "llm"`, `reason` names a
sense mismatch); the staging line APPLYs (`Restart the Kivi pod in
staging before the client demo tomorrow.`) even though it shares **no**
neighbor words with the teach sentence — the deleted cue gate could never
have applied it from lexical overlap alone.

**G. Common word vs product.** `Groww`/`grow` with no `teach_text` — the
gardening sentence should ABSTAIN.

```
uv run kivi reset
uv run kivi observe --source dictionary_add --canonical Groww --forms grow
uv run kivi run --formatted "The plants will grow faster in the sun."
```

Expected: ABSTAIN (`helper: "llm"`). Compare to §7.1E, where
`--decide ungated` APPLYs the homograph with no sense check.

**H. Same word, two senses, one sentence — batched into one call.** `grow`
appears twice: once as the brand (moved funds *from* it), once as the
ordinary verb (profits didn't grow). Both are scored by a single LLM call,
not two.

```
uv run kivi reset
uv run kivi observe --source dictionary_add --canonical Groww --forms grow,groww \
  --context "He opened a mutual fund SIP on Groww last month."
uv run kivi run \
  --formatted "Move the stocks and SIPs from grow as the profits didnt grow last FY." --json
```

Expected: `"...from Groww as the profits didnt grow last FY."` — the first
`grow` (brand) APPLYs, the second (verb) ABSTAINs. In the JSON, both
`TokenDecision`s have `helper: "llm"`, different `llm_score`s, and the
top-level `model_calls` is `1`, not `2` — one call scored both occurrences.

## 8. Evaluation

The command the review agent should run (no key, matches the committed
snapshot):

```
uv run kivi --decide ungated eval
```

Reads `eval/dataset/teaches.csv` + `eval/dataset/cases.csv` only. Isolated
SQLite per case row. Headline is hits, not a pass count: expected vs
actual APPLY hits, TP/FP/FN, precision/recall. Rows marked
`requires_llm=true` SKIP (not FAIL) under `--decide ungated`. Exit status
is non-zero on any string mismatch or run error.

Expected: `31` rows ran (`4` SKIPPED), `25/25` expected hits, 0 FP/FN,
precision 1.00, recall 1.00. That is the committed file
`eval/results/latest.md`.

`uv run kivi eval` defaults to `--decide llm` and **requires**
`KIVI_LLM_API_KEY` plus `KIVI_LLM_MODEL`. It also scores the 4
`requires_llm` rows, and it will **not** match the committed snapshot —
live-model variance, not a code regression. See
[eval/dataset/README.md](eval/dataset/README.md#requires_llm). The
deterministic proof of the 4 sense-check scenarios is
`tests/test_llm_helper.py` (mocked HTTP).

## 8.1 End-to-end script (train + test + latency + annotations, one command)

```
uv run python scripts/e2e_demo.py --decide ungated
uv run python scripts/e2e_demo.py --decide llm
```

Trains 7 fresh memories (product/fruit homograph, brand/verb homograph,
personal-name respelling, phonetic-only brand, a conflicting-canonical pair,
and one deliberate learner refusal), then runs 9 long, unique paragraphs
against `kivi --profile auto run --json` — none of them are reused from
`eval/dataset/` or the demos above. For every test it prints the input, the
memory-aware output, and a full per-token annotation table (`decision`,
`reason`, `matched_via`, `helper`, `model`, and the LLM call's own
`llm_latency_ms`), plus a run-level `latency_ms`/`model_calls` and a final
summed total. Isolated SQLite at `data/e2e_demo.sqlite`, wiped and
retaught from scratch on every run — never touches `data/kivi.sqlite`.

Run it once with `--decide ungated` and once with `--decide llm` to see
retrieve latency vs gated quality directly (same 9 sentences, same
pipeline).

## 8.2 Stress test (10,500+ words, partially taught, full metrics)

```
uv run python scripts/stress_test/run_stress_test.py --limit 10                 # ungated latency
uv run python scripts/stress_test/run_stress_test.py --decide ungated           # full ungated
uv run python scripts/stress_test/run_stress_test.py --decide llm --limit 10    # gated, needs key+model
```

A larger, synthetic, deliberately confusing corpus (183 paragraphs, 58
vocabulary items across name respellings / brand-vs-common-word homographs
/ phonetic-only terms), with only 60% of that vocabulary taught before the
corpus runs — see `scripts/stress_test/README.md` for the full design and
measured numbers (ungated: 240 found / 141 extra / 0 missed, precision
0.630, recall 1.000, ~16 ms typical paragraph; gated Haiku smoke on 20
paragraphs: 0 extras). Reports found/extra/missed, latency percentiles,
HTTP calls, token usage, and an estimated cost. `--decide ungated` is
the default (committed snapshot). `--decide llm` needs key + model.
See README [Metrics](README.md#metrics).

## 9. Where results are written

- `eval/results/latest.json` / `.md` — `kivi eval`, part of the submission
- `scripts/stress_test/results/latest.json` / `.md` — the stress test's
  committed snapshot is the free ungated baseline; a gated re-run
  overwrites it locally with non-deterministic (real API) numbers, so
  don't commit a gated run over it

Re-running either overwrites its own files.

## 10. Reset

Wipe the live store:

```
uv run kivi reset
```

Wipe and replay seed:

```
uv run kivi reset --seed
```

After wipe, `uv run kivi memories` is `[]`. After `--seed`,
it matches `data/seed/observations.json` replay, not the previous demo.
