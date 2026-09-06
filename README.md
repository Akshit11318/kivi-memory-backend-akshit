# Kivi Memory Lab

A **per-user word notebook**. Not speech-to-text, not a formatter, not
chat memory, not a knowledge graph.

Kivi already turns speech into **ASR text**, then a language model into
**formatted text**. Those two are inputs. This lab produces the **third**
transcript: this user’s spellings — or it **leaves the line alone**.

```
said      rustam called from nilgiri
typed     Rustam called from Nilgiri.
written   Rustom called from Nilgiri.
```

Primary review: local CLI + SQLite. Exact commands: [RUN.md](RUN.md).
Full contracts: [plan.md](plan.md).

---

## What is in the box vs what is outside

We never record audio. We never own the formatter. Memory is **found
and used as if it were placed in the formatting prompt**. The rewriter
and the optional LLM producer are stand-ins for that.

```mermaid
flowchart LR
  subgraph outside [Existing_Kivi_not_this_repo]
    Speech --> ASR
    ASR --> AsrText[ASR_text]
    AsrText --> FormatterLM
    FormatterLM --> Formatted[formatted_text]
  end

  subgraph lab [This_repo]
    AsrText --> Pipeline
    Formatted --> Pipeline
    Store[SQLite_word_notebook] --> Pipeline
    Pipeline --> Third[memory_aware_text]
    Pipeline --> Trace[why_APPLY_or_ABSTAIN]
  end
```

Two clocks, one store:

```mermaid
flowchart TB
  subgraph learn [Learning_observe]
    Obs[Observation] --> Learner
    Learner --> Store
  end

  subgraph infer [Inference_run]
    AsrIn[ASR] --> Pipeline
    FmtIn[formatted] --> Pipeline
    Store --> Pipeline
    Pipeline --> Out[third_transcript_plus_trace]
  end

  Reset[kivi_reset] -->|wipe| Store
  Seed[seed_json] -->|reset_seed| Store
```

---

## A memory is a word, not a sentence

Each row is one identity for one user:

| Field | Meaning |
| --- | --- |
| `canonical` | how they write it (`Rustom`, `Kivi`) |
| `forms` | how it has appeared (`rustam`, `kiwi`) |
| `confidence` | 1.0 dictionary; 0.85 first correction |
| `context_cues` | ±2 neighbor content words from the teach line |
| `evidence` | which observations created the row |

We do **not** store “Rustom is a friend” or the whole utterance.

```mermaid
flowchart LR
  Teach["correction: Kiwi to Kivi\nin 'review the sarvam kiwi service'"]
  Teach --> Row
  subgraph Row [Memory_row]
    C[canonical_Kivi]
    F[forms_kiwi_Kiwi]
    Q[confidence]
    N[cues_sarvam_review_service]
  end
```

---

## Learning (`kivi observe`)

User-asserted only. No harvesting unusual words from raw ASR.

```mermaid
flowchart TB
  In[observe] --> Src{source}
  Src -->|dictionary_add| Dict[canonical plus forms]
  Src -->|correction| Diff[word_diff formatted vs final]
  Diff --> Gate{grapheme_gate}
  Gate -->|Friday_to_Thursday| NoLearn[no_memory]
  Gate -->|there_to_their| NoLearn
  Gate -->|Rustom_ok| Upsert
  Dict --> Upsert[one_row_per_canonical]
  Upsert --> Cues[if_sentence_present\nunion_plusminus_2_content_tokens]
  Cues --> Store[SQLite]
```

Same `user_id` + same `canonical` → **merge forms and cues**, do not
duplicate the row.

---

## Inference (`kivi run`) — this is the live path

`--profile` picks the path. Default is `exact`. No API key required.

```mermaid
flowchart TB
  ASR[ASR_text] --> Gate{profile}
  FMT[formatted_text] --> Gate
  Gate -->|off| Pass[return_formatted_unchanged]
  Gate -->|exact_or_phonetic_or_llm| Tok[tokenize_strip_quotes_possessives_hyphens]
  Tok --> Ret{retriever}
  Store[SQLite] --> Ret
  Ret -->|exact| Exact[normalized_form_overlap]
  Ret -->|phonetic| Phon[Double_Metaphone]
  Exact --> Align
  Phon --> Align
  Align[SequenceMatcher_ASR_to_formatted\nnever_positional_1to1]
  Align --> Dec[decide_per_formatted_token]
  Dec --> T1{confidence_gte_0.75}
  T1 -->|no| Abs1[ABSTAIN]
  T1 -->|yes| T2{unique_canonical}
  T2 -->|conflict| Abs2[ABSTAIN_conflict]
  T2 -->|yes| T3{token_neq_canonical}
  T3 -->|already_right| Abs3[ABSTAIN]
  T3 -->|differs| T4{cues_empty_or_overlap}
  T4 -->|cues_set_and_no_overlap| Abs4[ABSTAIN_context_mismatch]
  T4 -->|ok| Apply[APPLY]
  Apply --> Prod{producer}
  Abs1 --> Pass
  Abs2 --> Pass
  Abs3 --> Pass
  Abs4 --> Pass
  Prod -->|exact_or_phonetic| Rew[rewrite_APPLY_tokens_only]
  Prod -->|llm| LLM[glossary_of_chosen_words_in_prompt]
  Prod -->|off_or_all_abstain| Pass
  Rew --> Third[memory_aware]
  LLM --> Third
  Pass --> Third
  Third --> Trace[trace_plate]
```

**Why `kiwi` / `Kivi` needs the cue gate**

```mermaid
flowchart LR
  subgraph teach [Taught_on_work_line]
    W["review the sarvam kiwi service"]
    W --> Cues["cues: sarvam, review, service"]
  end

  subgraph work [Later_work]
    W2["Ask … to review the Sarvam Kiwi service."]
    Cues --> Hit[window_overlaps] --> APPLY
  end

  subgraph grocery [Later_grocery]
    G["Remind me to buy kiwi tomorrow."]
    Cues --> Miss[no_overlap] --> ABSTAIN
  end
```

Empty cues (dictionary add with no sentence) → no gate. That word
applies anywhere.

Phonetic only **finds** `kiwi` when you stored `Kivi`. Cues decide
whether that find is allowed to rewrite.

---

## Profiles

| Profile | Retriever | Producer | Key |
| --- | --- | --- | --- |
| `off` | — | pass through | no |
| `exact` | string overlap | rewrite | no |
| `phonetic` | Metaphone | rewrite | no |
| `llm` | exact | memories in a format prompt | optional |

Unknown `--profile` errors. It does not fall back.

```mermaid
flowchart LR
  P[kivi_run] --> off
  P --> exact
  P --> phonetic
  P --> llm
  off --> Same[formatted_equals_output]
  exact --> Note[notebook_plus_rewrite]
  phonetic --> Note
  llm --> Prompt[notebook_plus_LM]
```

---

## Modules (closed list)

Nothing else ships. Align lives inside `pipeline`, not as a second
product.

```mermaid
flowchart TB
  CLI[cli] --> CFG[config]
  CLI --> Pipe[pipeline]
  Pipe --> Ret[retrieve]
  Pipe --> Align[align]
  Pipe --> Dec[decide]
  Pipe --> Prod[produce]
  CLI --> Learn[learner]
  Learn --> Store[store]
  Ret --> Store
  Pipe --> Trace[trace]
  Eval[eval] --> Pipe
  Eval --> Store
```

| Folder | Job |
| --- | --- |
| `cli/` | flags, notebook skin, print traces |
| `config/` | paths, profile names, thresholds |
| `store/` | SQLite, migrate, **reset** |
| `learner/` | observation → memory |
| `retrieve/` | `exact` \| `phonetic` |
| `pipeline/` | wire + ASR↔formatted align |
| `decide/` | per-token APPLY / ABSTAIN + cue gate |
| `produce/` | `passthrough` \| `rewrite` \| `llm` |
| `trace/` | inspectable run record |
| `eval/` | fixtures × profiles |

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

---

## Libraries and modules

The runtime is **Python 3.13** installed and locked by **uv** (`uv.lock`).
**hatchling** only builds the wheel. We do not use pip as the review
path, and we do not pull SQLAlchemy, transformers, Hugging Face, a
vector DB, or an agent host.

The only third-party **runtime** library is **jellyfish**: Double
Metaphone for the `phonetic` profile. Everything else is the standard
library on purpose so a clone can `uv sync` and run `exact` / `off`
with no keys.

| Piece | Kind | What we use it for |
| --- | --- | --- |
| **uv** | toolchain | `uv sync`, `uv run kivi`, lockfile |
| **Python 3.13** | language | whole lab |
| **hatchling** | build | package `src/kivi_memory` |
| **jellyfish** | runtime dep | Metaphone keys in `retrieve/phonetic` |
| **sqlite3** | stdlib | durable notebook; migrate; `reset` |
| **difflib.SequenceMatcher** | stdlib | correction word-diff; ASR↔formatted align (never 1:1 index) |
| **argparse** | stdlib | CLI flags and subcommands |
| **json** | stdlib | seed, inspect, eval results |
| **dataclasses / pathlib / datetime** | stdlib | records, paths, timestamps |
| **os / sys** | stdlib | `NO_COLOR`, `--plain`, process exit |
| **pytest** | dev only | `uv run pytest`; not needed to demo |
| **Gemini / Groq HTTP** | optional, not a pinned dep yet | `--profile llm` only; skipped if no key |

**Our packages** (closed list — do not add folders):

| Module | Use |
| --- | --- |
| `cli/` | flags, notebook skin, print |
| `config` | paths, profiles, thresholds |
| `domain/` | Memory, Observation, protocols |
| `store/` | SQLite + schema |
| `learner/` | explicit observe; grapheme gate; neighbor cues |
| `retrieve/` | exact overlap; phonetic |
| `pipeline/` | wire + align |
| `decide/` | APPLY / ABSTAIN + context mismatch |
| `produce/` | passthrough, rewrite, llm |
| `trace/` | inspectable run plate |
| `eval/` | fixtures × profiles |

---

## Commands

```
uv sync
uv run kivi
uv run kivi observe …
uv run kivi memories
uv run kivi run --asr "…" --formatted "…" --profile exact
uv run kivi eval --profiles off,exact,phonetic,llm
uv run kivi reset
uv run kivi reset --seed
```

`--plain` / `NO_COLOR` turn off the skin.

Eval, seed fixtures, and some commands are still landing in stages
([HANDOFF.md](HANDOFF.md)). The diagrams above are the **target**
system the submission must match, not a second architecture.
