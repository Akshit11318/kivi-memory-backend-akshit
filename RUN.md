Completely local application. Python 3.13+ via uv. SQLite file on disk.
Default profile (`auto`) needs no environment variables — it runs ungated
without a key. No hosted URL.

## 1. Runtimes

- Python 3.13+
- uv 0.4+

## 2. Environment variables

All optional. Unset entirely, `auto` runs the full retrieve cascade and
cheap decide doors, then APPLYs ungated (no sense check) once a candidate
survives — see README "LLM sense helper".

| Variable            | Default                                            | Purpose                                  |
| -------------------- | --------------------------------------------------- | ------------------------------------------ |
| `KIVI_LLM_API_KEY`    | unset                                                | enables the LLM sense helper (last vote for APPLY vs ABSTAIN) |
| `KIVI_LLM_BASE_URL`   | `https://openrouter.ai/api/v1`                       | OpenAI-compatible chat completions host  |
| `KIVI_LLM_MODEL`      | `google/gemma-4-26b-a4b-it:free`                     | model id                                  |

Copy `.env.example` to `.env` and fill in a key to try the gated demos in
§7.2. Never commit a real key.

```
cp .env.example .env
export $(grep -v '^#' .env | xargs)
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

**Run** a *new* line (same terms, different sentence, default `--profile
auto`). Expected: APPLY on all three, written
`Ping Akshit after the Postgres and Grafana deploy.`

```
uv run kivi run \
  --asr "ping akshith after the postgress and graffana deploy" \
  --formatted "Ping Akshith after the postgress and graffana deploy."
```

**Deliberate no-op** (nothing in the notebook matches). Expected:
ABSTAIN, formatted unchanged, `no_memory`.

```
uv run kivi run \
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
(`exact` | `phonetic` | `null`) and `helper` (`llm` | `ungated` | `null`)
per token.

### 7.1 Demos that run with no key

All of these use the live store `data/kivi.sqlite` (created on first
open). Do not pass `--db`. Start each block with `uv run kivi reset` so
leftover rows from the last demo do not leak in.

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
uv run kivi run --asr "im gonna ask akshith" --formatted "I'm going to ask Akshith."
```

Expected: APPLY, written `I'm going to ask Akshit.`

**B. `exact` vs `auto` — the graffana paragraph.** `Grafana` is stored with
no `graffana` form. `exact` cannot find it; `auto` falls through to the
phonetic retriever in the same cascade.

```
uv run kivi reset
uv run kivi observe --source dictionary_add --canonical Grafana --forms grafana
uv run kivi --profile exact run --formatted "Please restart the graffana pod."
uv run kivi --profile auto run --formatted "Please restart the graffana pod."
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
uv run kivi run --formatted "Ria sent the deck." --json
```

In the JSON, the `Ria` token is ABSTAIN `conflicting_canonicals` with
`memory_ids` listing both rows, `helper: null` — the LLM is never called
once a cheap door has already closed.

**E. No key, documented: a homograph rewrites everywhere.** Without
`KIVI_LLM_API_KEY`, `kiwi`/`Kivi` has no sense check, so it rewrites the
grocery sentence too, not just the work one.

```
uv run kivi reset
uv run kivi observe --source correction \
  --formatted "Please review the Sarvam Kiwi rollout." \
  --final "Please review the Sarvam Kivi rollout."
uv run kivi run --formatted "Remind me to buy kiwi tomorrow."
```

Expected: APPLY, written `Remind me to buy Kivi tomorrow.` (`helper:
"ungated"` in `--json`). This is the default, not a bug — see README
"LLM sense helper".

### 7.2 Demos that need `KIVI_LLM_API_KEY`

Set a real key first (§2). These show the sense check §7.1E documents the
absence of.

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

Expected: ABSTAIN (`helper: "llm"`). Compare to demo B-style behavior with
no key, where this would APPLY ungated instead.

## 8. Evaluation

```
uv run kivi eval
```

Reads `eval/dataset/teaches.csv` + `eval/dataset/cases.csv` only — no JSON
eval tree. Isolated SQLite per case row. Headline is hits, not a pass
count: expected vs actual APPLY hits, TP/FP/FN, precision/recall, per
profile and overall. Rows marked `requires_llm=true` SKIP (not FAIL) when
no key is set. Exit status is non-zero on any string mismatch or run
error.

With no key: `31` rows run (`4` SKIPPED), `25/25` expected hits, 0 FP/FN,
precision 1.00, recall 1.00. **This no-key run is the committed, graded
snapshot** — deterministic and reproducible.

Setting `KIVI_LLM_API_KEY` also runs the 4 `requires_llm` rows, but it
changes *every* row's decide path, not just those 4 — any token that clears
the cheap doors now asks the live model instead of falling through to
ungated APPLY. A free/small model's judgment on an ordinary-looking token
with no `teach_text` (e.g. `grow`, `archive`, `film`) is genuinely
inconsistent run to run, so expect `kivi eval` with a key to disagree with
the no-key snapshot on rows outside the 4 `requires_llm` ones — that is
live-model variance, not a code regression. See
[eval/dataset/README.md](eval/dataset/README.md#requires_llm). The
deterministic proof of the 4 must-work scenarios is
`tests/test_llm_helper.py`, which mocks the HTTP call.

## 9. Where results are written

- `eval/results/latest.json`
- `eval/results/latest.md`

Those files are part of the submission. Re-running eval overwrites them.

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
