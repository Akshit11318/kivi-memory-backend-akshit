# Kivi Memory Lab

A **per-user word notebook**. Not speech-to-text, not a formatter, not
chat memory, not a knowledge graph, not RAG.

Kivi already turns speech into **ASR text**, then a language model into
**formatted text**. Those two are inputs. This lab produces the **third**
transcript: this user's spellings — or it **leaves the line alone**.

```
said      ask akshith to bump postgress and graffana
typed     Ask Akshith to bump postgress and graffana.
written   Ask Akshit to bump Postgres and Grafana.
```

Primary review: local CLI + SQLite. Exact commands: [RUN.md](RUN.md).

---

## What it can distinguish

Doing nothing is half the product. Every row below is a committed eval
row in `eval/dataset/cases.csv` with an asserted hit or no-op, not a claim —
run `uv run kivi eval` to reproduce (see [Evaluation](#evaluation)).

| Situation                                                                          | What it does                                     | Why                                                                                     |
| ----------------------------------------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Taught spelling, matching use (`Akshith` → `Akshit`)                                | **APPLY**                                         | Exact retrieve finds the stored form, confidence ≥ 0.75, token ≠ canonical               |
| Formatter expanded the line (`im gonna ask akshith` → `I'm going to ask Akshith.`)  | **APPLY** on `Akshith` only                        | Alignment is a `SequenceMatcher` diff, never index `i`                                   |
| Unseen phonetic variant (`graffana` when only `Grafana` was stored)                 | `exact` **ABSTAIN**, `auto`/`phonetic` **APPLY**   | Retrieve cascade: exact first, phonetic on miss. Proves the two retrievers aren't redundant |
| Brand that is also a common word, wrong sense (`buy kiwi at the store`, key set)     | **ABSTAIN** `sense_mismatch`                       | The LLM sense helper is the last vote, not lexical overlap                               |
| Same brand, unrelated neighbor words but the right sense (`restart the Kiwi pod in staging`, key set) | **APPLY**                          | No shared vocabulary with the teach sentence at all — sense, not cue overlap              |
| No key configured                                                                   | **APPLY ungated** once a candidate survives the cheap doors | Documented default, not hidden: see [LLM sense helper](#llm-sense-helper---last-vote-no-cue-fallback) |
| Already spelled right, or only case differs (`Meera`, `sarvam`)                     | **ABSTAIN** `already_canonical`                    | Case is not a correction signal; the formatter owns capitalization                        |
| Two real people, one surface (`Riya` and `Ria`)                                     | **ABSTAIN** `conflicting_canonicals`               | Never guess an identity by ranking confidence                                             |
| Content edit or grammar fix (`Friday`→`Thursday`, `there`→`their`)                  | **Learns nothing**, 0 rows                         | Grapheme gate + closed homophone refuse list, not a threshold                             |
| Multi-token compound (`blink it` → `Blinkit`)                                       | **ABSTAIN** `no_memory`                            | One token → one token is the whole abstraction                                            |
| Empty input                                                                          | **ABSTAIN**, no crash                              | Cold path is a no-op                                                                       |

---

## Architecture

We never record audio. We never own the formatter. This lab stands in
for "put the chosen words into formatting." No cue gate anywhere in the
live path — sense disambiguation for a single surviving candidate is the
LLM helper's job, or an explicit ungated default with no key.

The product is two clocks and one store. ASR is never mined.

```mermaid
flowchart TB
  subgraph outside [Not this repo]
    Speech --> ASR
    ASR --> Formatter
    Formatter --> Formatted
  end

  subgraph clock1 [Clock 1 — teach  kivi observe]
    Dict[dictionary_add] --> Learner
    Corr[correction: formatted vs final] --> Learner
    Learner --> Gate{grapheme + homophone + not both-function}
    Gate -->|no| Skip[0 rows]
    Gate -->|yes| Row[(SQLite memory)]
  end

  subgraph clock2 [Clock 2 — speak again  kivi run]
    ASR2[new ASR] --> Pipe
    Formatted2[new formatted] --> Pipe
    Row --> Pipe
    Pipe --> Third[third transcript]
    Pipe --> Why[APPLY or ABSTAIN + reason]
  end
```

`kivi reset` wipes the store. `kivi reset --seed` replays
`data/seed/observations.json`.

### A memory is a word, not a sentence

Each row is one identity for one user.

| Field        | Meaning                                                          |
| ------------ | ----------------------------------------------------------------- |
| `canonical`  | how they write it (`Akshit`, `Postgres`)                          |
| `forms`      | how it has appeared (`akshith`, `postgress`)                      |
| `confidence` | 1.0 dictionary; 0.85 first correction; +0.05/correction, cap 1.0  |
| `teach_text` | the correction sentence, or an optional `dictionary_add` example — evidence for the LLM prompt, **never a gate** |

We do **not** store "Akshit is a colleague" or the whole utterance.
Admission test: if deleting the row cannot change a future transcript's
wording of a personal term, it is not this memory.

Same `user_id` + same `canonical` → merge forms, do not duplicate the row.
`teach_text` is replaced by the newer evidence on a later teach, not unioned
— it is a prompt hint, not an accumulating gate.

### Clock 1 — what gets into the notebook

`kivi observe`. User-asserted only.

```mermaid
flowchart TB
  Obs{source}
  Obs -->|dictionary_add| D[canonical + forms  confidence 1.0]
  D --> T1{--context passed?}
  T1 -->|no| NoText[teach_text = null]
  T1 -->|yes| Text1[teach_text = the example sentence]
  Obs -->|correction| Diff[SequenceMatcher word diff]
  Diff --> Only1{1 token to 1 token?}
  Only1 -->|insert / delete / 2-for-1| Skip1[not a candidate]
  Only1 -->|yes| G{passes_grapheme_gate}
  G -->|Friday / Thursday| Skip2[not_grapheme_similar]
  G -->|there / their| Skip3[refused_homophone]
  G -->|its / it's function| Skip4[both_function_words]
  G -->|Akshith / Akshit| Upsert[one row per user + canonical]
  Upsert --> Text2[teach_text = the final sentence]
```

### Clock 2 — a new line comes in

`kivi run`. `--profile off` returns formatted and stops.

```mermaid
flowchart TB
  In[ASR + formatted] --> Tok[tokenize formatted]
  Tok --> Align[align each formatted token to ASR tokens]
  Align --> Surfaces[lookup keys = formatted core + aligned ASR word]
  Surfaces --> Casc{retrieve cascade}
  Casc -->|exact hit| ExactOK[matched_via = exact]
  Casc -->|exact miss, auto/phonetic| Ph[Metaphone + v/w swap + same first letter]
  Ph -->|hit| PhOK[matched_via = phonetic]
  Ph -->|miss| None[matched_via = null]
  ExactOK --> Doors
  PhOK --> Doors
  None --> Doors[cheap doors]
  Doors --> Rew[rewrite only APPLY tokens]
  Rew --> Out[written line + per-token why]
```

### Retrieve cascade — exact then phonetic, one on-path

Per token, the lookup keys are the formatted core plus the
`SequenceMatcher`-aligned ASR token (never a positional index).

1. `exact.retrieve(surfaces)`. Any candidates → stop, `matched_via = "exact"`.
   Exact always wins when the surface is already a stored form.
2. Else `phonetic.retrieve(surfaces)`. Any candidates →
   `matched_via = "phonetic"`.
3. Else no candidates, `matched_via = null`.

`--profile auto` (**default**) runs this cascade. `--profile exact` and
`--profile phonetic` force a single retriever — an ablation flag, not a
different decide path: both still run the same cheap doors and LLM helper
below. `--profile off` skips retrieval entirely and returns formatted
unchanged.

### Decide — cheap doors, first no wins

```mermaid
flowchart TD
  Start[candidates for this token] --> A{any?}
  A -->|no| N[ABSTAIN  no_memory]
  A -->|yes| B{one canonical?}
  B -->|Riya and Ria both match| C[ABSTAIN  conflicting_canonicals]
  B -->|yes| D{confidence >= 0.75?}
  D -->|no| L[ABSTAIN  low_confidence]
  D -->|yes| E{token already is the canonical?}
  E -->|yes| AC[ABSTAIN  already_canonical]
  E -->|no| Helper{KIVI_LLM_API_KEY set?}
  Helper -->|yes| LLM[LLM: APPLY or ABSTAIN + reason]
  Helper -->|no, or timeout, or parse fail| Ungated[APPLY  helper=ungated]
```

No cue gate anywhere in this path. There is no closed word list standing in
for one either.

### LLM sense helper — last vote, no cue fallback

The model does not find names and does not write SQLite. Once exactly one
candidate memory survives the cheap doors, it answers one question:
**REPLACE this token in this sentence, or ABSTAIN.**

Prompted with only: the current formatted sentence, the token, the stored
canonical + forms, and `teach_text` if the memory has one. No world
knowledge instruction: APPLY only for the same personal/product spelling in
*this* sentence; ABSTAIN for fruit vs brand, common word vs product, a
different person, or grammar. Temperature 0, ~15s timeout, one call per
token that reaches this stage.

**No key, a timeout, or an unparseable response all fall through to the
same ungated APPLY** (`helper = "ungated"`, `reason = "ungated"`). This is
not a bug to patch later — it is the documented default. It means, with no
key:

- `Groww`/`grow` rewrites `"The plants will grow faster in the sun."` to
  `"...will Groww faster..."` — wrong, and expected.
- `kiwi`/`Kivi` rewrites the grocery sentence too, not just the work one.
- `Karan`/`Karen` and `Sanjay`/`Sanjeev` still misfire under `--profile
  phonetic` / the grapheme gate respectively — the LLM cannot fix a
  collision it is never asked to arbitrate. See [Limitations](#limitations).

`kivi eval` SKIPS (does not fail) any row whose behavior depends on real
sense-gating when no key is configured — see
[eval/dataset/README.md](eval/dataset/README.md).

Provider: OpenAI-compatible HTTP (OpenRouter-style), one module
(`decide/llm_helper.py`), stdlib `urllib` only — no new HTTP dependency, and
the eval CSV runner calls the same module rather than duplicating the
request.

---

## Profiles

| Profile    | Retriever                          | Decide                       | Status            |
| ---------- | ----------------------------------- | ----------------------------- | ------------------ |
| `off`      | —                                    | none, passthrough              | shipped            |
| `exact`    | string overlap only (ablation)      | cheap doors + LLM/ungated      | shipped            |
| `phonetic` | classic Metaphone + `v↔w` (ablation) | cheap doors + LLM/ungated      | shipped            |
| `auto`     | exact → phonetic cascade            | cheap doors + LLM/ungated      | shipped (**default**) |

Unknown `--profile` errors. It does not fall back.

---

## Assumptions

These are bets the diagrams above rest on. They are not hidden.

- **ASR and formatted text already exist.** This repo does not hear audio
  and does not format speech. The only output is the third transcript, or
  the formatted line unchanged.
- **The user asserts a spelling.** Writes come from `dictionary_add` or a
  1:1 `correction`. Unusual words in raw ASR are not harvested.
- **One token maps to one token.** Inserts, deletes, and compounds
  (`blink it` → `Blinkit`) are sentence edits, not memory.
- **Case belongs to the formatter.** `Meera` / `meera` is not a teach
  signal and not a rewrite.
- **Sense disambiguation is the LLM's job, not a token-overlap gate.**
  There is no cue bag, and no closed word list standing in for one. Without
  a key the system is explicit about being ungated, not silently wrong.
- **Conflict is not a ranking problem.** Two canonicals for one surface
  → ABSTAIN. We do not pick the higher confidence.
- **Letters are not identity.** `Lakshmi`/`Laxmi` and `Sanjay`/`Sanjeev`
  can look the same to every string rule we have, and `Karan`/`Karen` share
  a Metaphone code. Speaker identity is out of scope; the LLM helper checks
  *sense* in one sentence, not *who said it* — these collisions stay
  documented, not silently fixed.
- **Review is local.** SQLite on disk, no daemon. The LLM helper is the one
  optional network call, off by default (no key = ungated, not blocked).

---

## Decisions

| Decision                                                          | Why                                                              |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Memory is a lexical row, not a chat log                            | The brief is phonetic / word-level memory, not personal AI       |
| Learn only from Dictionary add or a 1:1 spelling correction        | Ordinary use; ASR alone must not write the notebook              |
| Retrieve is exact-then-phonetic, one cascade, no matrix of gates   | Exact is cheap and precise; phonetic recovers what exact misses  |
| Sense disambiguation is an LLM last vote, not a cue gate           | A cue gate needs lexical overlap with the teach sentence and cannot generalize; an LLM reasons about sense from one sentence alone |
| No key → ungated APPLY, not ABSTAIN, not a cue fallback            | An undocumented fallback would silently resurrect the deleted gate; an honest ungated default does not |
| APPLY iff confidence ≥ 0.75, unique canonical, token ≠ canonical, then LLM/ungated | Weak or conflicting evidence → do nothing before ever asking the model |
| First correction is 0.85, not 0.60                                 | One teach must be enough                                          |
| `auto` is the default review path                                  | Cascade retrieve, inspectable, resettable, works with or without a key |
| `off` is a profile, not a missing store                            | Lets eval tell "memory did nothing" from "memory is disabled"     |
| Alignment is `SequenceMatcher`, never index `i`                    | Formatters expand contractions and drop fillers                   |
| No Hugging Face, no vector DB, no entity graph, no embeddings      | Out of scope for this edge                                        |

---

## Limitations

- **Alignment** works when ASR and formatted tokens mostly correspond. It degrades on a heavy formatter paraphrase.
- **Grapheme gate** requires the same first letter and a similarity floor. `film` → `vLLM` cannot be learned from a correction; use `dictionary_add`.
- **Homophone refuse list** is closed (`there`/`their`, `your`/`you're`, …). New grammar pairs are not inferred.
- **One token → one token.** Compounds (`fast api` → `FastAPI`) are structural ABSTAIN, not a miss we pretend to fix.
- **No key means no sense check.** Without `KIVI_LLM_API_KEY`, any token that clears the cheap doors APPLYs — `Groww`/`grow` rewrites gardening sentences, `kiwi`/`Kivi` rewrites grocery lists. This is the documented default (see [LLM sense helper](#llm-sense-helper---last-vote-no-cue-fallback)), not a bug — there is no cue-based middle ground reintroduced to soften it.
- **The LLM helper does not solve speaker identity.** `Sanjay → Sanjeev` passes the correction grapheme gate (same first letter, ratio 0.77) and gets learned as if it were a respelling; `--profile phonetic` also collides `Karan`/`Karen` (identical Metaphone code). The helper is asked "same sense in this sentence," never "same person as the speaker meant" — it has no signal to arbitrate that, and neither did the cue gate it replaced. `eval/dataset/cases.csv` asserts both misfires happen under the default rather than hiding them (`karan_karen_limitation`, `sanjay_sanjeev_limitation`).
- **Phonetic** uses `jellyfish` classic Metaphone (one code), plus a `v↔w` swap so `kiwi`/`kivi` can meet, plus a first-letter rule to kill short-token collisions (`Ravi`/`Robbie`, `Kavi`/`Covey`). It is not Double Metaphone. Unseen transliterations often miss.
- **No online reject loop.** A bad APPLY is not unlearned from a later tap.
- **The LLM call, when made, is a live network dependency.** Timeout ~15s; on timeout or an unparseable response the token still resolves (ungated APPLY), so a flaky provider degrades to the no-key behavior rather than hanging or crashing — but it does mean eval rows scored with a key can vary run to run if the provider's answer does.

---

## Evaluation

How we evaluate is part of the brief. There is no hidden benchmark.

- Dataset: `eval/dataset/teaches.csv` (setup) + `eval/dataset/cases.csv`
  (inputs and expectations). Case intent is documented in
  [eval/dataset/README.md](eval/dataset/README.md).
- Runner: isolated SQLite per case row, real pipeline `run()`, no duplicated
  decide/HTTP logic.
- Headline: **hits**, not a pass count. `expected_hit` (`from -> to` in a
  case's `expected_hits`) vs `actual_hit` (a real APPLY) gives TP/FP/FN,
  precision, and recall — per profile and overall. A case's
  `expected_memory_aware`, if set, is also checked as an exact string match.
- `requires_llm=true` rows SKIP (not FAIL) with no `KIVI_LLM_API_KEY` —
  scoring them against the ungated default would be a lie about what ran.
- Exit code is non-zero on any string mismatch or run error.

Command:

```
uv run kivi eval
```

Results (committed): [eval/results/latest.md](eval/results/latest.md) and
`eval/results/latest.json`. Latest snapshot (no key — 4 `requires_llm` rows
SKIPPED): **25/25 expected hits, 0 FP, 0 FN, precision 1.00, recall 1.00**
across the 31 rows that ran.

---

## Modules (closed list)

Nothing else ships. Align lives inside `pipeline`, not as a second product.

```mermaid
flowchart TB
  CLI[cli] --> CFG[config]
  CLI --> Pipe[pipeline]
  Pipe --> Ret[retrieve]
  Pipe --> Align[align]
  Pipe --> Dec[decide.conservative]
  Pipe --> Helper[decide.llm_helper]
  Pipe --> Prod[produce]
  CLI --> Learn[learner]
  Learn --> Store[store]
  Ret --> Store
  Pipe --> Trace[trace]
  Eval[eval_runner] --> Pipe
  Eval --> Store
```

| Module                       | Job                                            |
| ----------------------------- | ------------------------------------------------ |
| `cli/`                        | flags, notebook skin, print traces               |
| `config.py`                   | paths, profile names, thresholds, LLM env names  |
| `store/`                      | SQLite, migrate, **reset**                       |
| `learner/`                    | observation → memory                             |
| `retrieve/`                   | `exact` \| `phonetic`                            |
| `pipeline/`                   | wire + ASR↔formatted align + retrieve cascade    |
| `decide/conservative.py`      | cheap doors (no candidate / conflict / low confidence / already canonical) |
| `decide/llm_helper.py`        | last vote — LLM APPLY/ABSTAIN, or ungated        |
| `produce/`                    | `passthrough` \| `rewrite`                       |
| `trace/`                      | inspectable run record                           |
| `eval_runner.py`               | CSV fixtures → hit precision/recall               |

---

## Reset and what you ship

Live memory is `data/kivi.sqlite` (not in git). Portable memory is
`data/seed/observations.json`.

```mermaid
flowchart LR
  Live[kivi.sqlite] --> Reset[kivi_reset]
  Reset --> Empty[empty_valid_store]
  Empty --> Seed[kivi_reset_seed]
  SeedJSON[observations.json] --> Seed
  Seed --> Live
```

After `kivi reset`, `kivi memories` is empty and valid. After
`kivi reset --seed`, memory equals the seed replay, not leftovers.

---

## Libraries

Python **3.13** via **uv** (`uv.lock`). **hatchling** builds the wheel.
We do not use pip as the review path. We do not pull SQLAlchemy,
transformers, Hugging Face, a vector DB, sentence-transformers, torch, or an
agent host.

The only third-party **runtime** library is **jellyfish** (classic
Metaphone for phonetic retrieval). The LLM sense helper uses stdlib
`urllib`, not a new HTTP dependency. A clone can `uv sync` and run every
profile with no keys — `auto` and `exact`/`phonetic` all just fall back to
ungated APPLY once a candidate survives the cheap doors.

| Piece                       | Kind        | What we use it for                        |
| --------------------------- | ----------- | ------------------------------------------ |
| **uv**                      | toolchain   | `uv sync`, `uv run kivi`, lockfile         |
| **Python 3.13**             | language    | whole lab                                  |
| **hatchling**               | build       | package `src/kivi_memory`                  |
| **jellyfish**                | runtime dep | Metaphone keys in `retrieve/phonetic`      |
| **sqlite3**                  | stdlib      | durable notebook; migrate; `reset`         |
| **urllib**                   | stdlib      | the one optional LLM HTTP call             |
| **difflib.SequenceMatcher**  | stdlib      | correction word-diff; ASR↔formatted align  |
| **argparse**                  | stdlib      | CLI flags                                  |
| **csv / json**                | stdlib      | teaches/cases, seed, inspect, eval results |
| **pytest**                    | dev only    | `uv run pytest`; not needed to demo        |

---

## Commands

See [RUN.md](RUN.md) for the reviewer path. Short list:

```
uv sync
uv run kivi
uv run kivi reset --seed
uv run kivi memories
uv run kivi observe --source correction --asr "…" --formatted "…" --final "…"
uv run kivi run --asr "…" --formatted "…"
uv run kivi eval
uv run kivi reset
```
