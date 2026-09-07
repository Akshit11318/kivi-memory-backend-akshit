Completely local application. Python 3.13+ via uv. SQLite file on disk.
Default profile (`exact`) needs no environment variables. No hosted URL.
No API key.

## 1. Runtimes

- Python 3.13+
- uv 0.4+

## 2. Environment variables

None. `off`, `exact`, and `phonetic` are local only.

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

**Run** a *new* line (same terms, different sentence). Expected: APPLY
and written `Ping Akshit after the Postgres and Grafana deploy.`

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

Optional Dictionary teach (no sentence → no cue gate; add `--context`
to scope a risky brand the same way a correction does):

```
uv run kivi observe --source dictionary_add --canonical Terraform --forms terrafrom
uv run kivi observe --source dictionary_add --canonical Groww --forms grow --context "check the Groww SIP dashboard"
```

`run --json` prints the full inspectable trace.

### 7.1 Five demos that show the range

All of these use the live store `data/kivi.sqlite` (created on first
open). Do not pass `--db`. Start each block with `uv run kivi reset`
so leftover rows from the last demo do not leak in.

**A. Alignment, not position.** The formatter turned 4 ASR tokens into
5 (`im gonna` → `I'm going to`). A positional `token[i] → token[i]`
system corrupts `I'm`. This one rewrites only the target.

```
uv run kivi reset
uv run kivi observe --source dictionary_add --canonical Akshit --forms akshith
uv run kivi run --asr "im gonna ask akshith" --formatted "I'm going to ask Akshith."
```

Expected: APPLY, written `I'm going to ask Akshit.`, why `applied Akshit`.

**B. A brand that is also an ordinary word, and how it learns.** Taught
from one work line, the memory refuses the grocery line. Correct that
one grocery line and a *new* grocery-shaped line starts working —
cues grow by union from real use, they are never guessed.

```
uv run kivi reset
uv run kivi observe --source correction \
  --formatted "Please review the Sarvam Kiwi rollout." \
  --final "Please review the Sarvam Kivi rollout."

uv run kivi run --formatted "Buy kiwi at the store."
```

Expected: ABSTAIN, why includes `context_mismatch`.

```
uv run kivi observe --source correction \
  --formatted "Buy kiwi at the store." \
  --final "Buy Kivi at the store."

uv run kivi run --formatted "Buy kiwi for the office."
uv run kivi run --formatted "Pack some kiwi and mango for the picnic."
```

Expected: office line APPLY `Buy Kivi for the office.`; picnic line
ABSTAIN (still the fruit).

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

**D. `exact` and `phonetic` are not redundant.** `Grafana` is stored
with no `graffana` form. Metaphone keys match; exact lookup does not.

```
uv run kivi reset
uv run kivi observe --source dictionary_add --canonical Grafana --forms grafana
uv run kivi --profile exact run --formatted "Please restart the graffana pod."
uv run kivi --profile phonetic run --formatted "Please restart the graffana pod."
```

Expected: `exact` ABSTAIN `no_memory`; `phonetic` APPLY, written
`Please restart the Grafana pod.`

**E. Two real people, one surface — and the full trace.** Both rows
match `Ria`, they disagree, so the token is refused and both memory
ids are named in the trace.

```
uv run kivi reset
uv run kivi observe --source dictionary_add --canonical Riya --forms ria
uv run kivi observe --source dictionary_add --canonical Ria --forms riya
uv run kivi run --formatted "Ria sent the deck." --json
```

In the JSON, the `Ria` token is ABSTAIN `conflicting_canonicals` with
`memory_ids` listing both rows.

Every token in a run carries a row like this: what was decided, why,
and which memories were consulted.

## 8. Evaluation

```
uv run kivi eval --profiles off,exact,phonetic
```

Isolated SQLite per case. Exit status is non-zero if any requested
profile has FAIL or ERROR. Currently 70/70 pass on `off`/`exact`/`phonetic`.

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