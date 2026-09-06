# Handoff — Claude Code

Copy everything below the line into Claude Code.

---

You are implementing **Kivi Memory Lab** in this repo. The spec is `plan.md` (final submission). The brief is `Kivi_Backend_Full_Stack_Task_Clean_Cover.pdf`. The backbone (Python 3.13 + uv + locked folders) already exists. **Do not invent modules, folders, or dependencies** that are not named in `plan.md`.

## How you must work

1. Build **in stages** (order below). Finish a stage, show what changed, then **ask me before you commit**.
2. If I say yes, commit that stage only. One logical commit per stage.
3. **No co-author tags.** Do not add `Co-authored-by:` for Claude, Cursor, or yourself. Commit message: 1–2 sentences, why not what. Use a HEREDOC. Do not amend unless I ask. Do not `--no-verify`. Do not push unless I ask. Do not change git config.
4. Read `plan.md` sections **Systems modules**, **Pinned contracts**, **Feature toggles**, **System prompt rules**, and **Submission requirements** before coding. Treat the system-prompt block as binding.
5. Default review path is `--profile exact`, **zero env vars**. Do not make LLM or Hugging Face required. No `transformers`, no HF deploy, no vector DB, no entity graph.
6. After each stage: `uv run kivi --help` or the stage’s tests must work.

Toolchain:

```
uv sync
uv run kivi --help
uv run pytest
```

## Stages (do not skip ahead)

**Stage 1 — Domain + store + reset**  
Dataclasses/protocols. SQLite schema (observations, memories, memory_forms, meta). `MemoryStore` migrate / upsert / list. `kivi reset` and `kivi reset --seed` (seed file may be empty JSON `[]` until Stage 6). After wipe, `kivi memories` is empty and valid.

**Stage 2 — Learner**  
`explicit` only. `dictionary_add` confidence 1.0. Correction via formatted→final word-diff + grapheme gate + `REFUSE_HOMOPHONE_PAIRS` (`there`/`their` must not learn). First correction 0.85, +0.05 merge, cap 1.0. Same canonical → one row, union forms.  
On correction with a sentence: store ±2 **content** neighbor tokens as `context_cues` (union, stoplist the/a/to/of/…). Dictionary add with no sentence → empty cues. `kivi observe` works.

**Stage 3 — Tokenize, retrieve exact, align, decide, rewrite**  
Punctuation/possessive/hyphen strip. `pipeline/align.py`: SequenceMatcher ASR↔formatted; **never positional 1:1**. Exact retriever. Conservative decide: APPLY iff `confidence >= 0.75`, unique canonical, token ≠ canonical; conflict → ABSTAIN.  
**Context gate:** if the memory has cues, APPLY only when the ±2 window around the token overlaps a cue; else ABSTAIN `context_mismatch`. Empty cues → no gate. Work `Kiwi`/`sarvam` APPLY; grocery `buy kiwi` ABSTAIN.  
`rewrite` + `passthrough`. `kivi run --profile exact` and `--profile off`. Unknown `--profile` → error, no fallback.

**Stage 4 — Trace + CLI complete**  
Full inspectable trace (ASR, formatted, retrieved, per-token decisions, APPLY/ABSTAIN, reason, memories used, profile, latency). Commands: observe, memories, run, reset, eval stub ok.  
Keep the existing CLI skin (`cli/art.py`, `cli/style.py`). Call `trace_frame` from `kivi_memory.trace.format`. Do not replace it with plain prints. Honor `--plain` and `NO_COLOR`.

**Stage 5 — Phonetic profile**  
`jellyfish` Double Metaphone retriever. Same decide + rewrite. `--profile phonetic`. Add the short-token false-positive concern as a case when you write fixtures.

**Stage 6 — Seed + eval fixtures**  
Write `data/seed/observations.json` and `eval/cases/*.json` for families in `plan.md` (1–16 and 17–27). Train = seed; test = held-out runs. Do not invent extra families. Do not lock fancy metric formulas beyond useful/unnecessary/incorrect APPLY, abstentions, latency, model_calls=0, store counts.

**Stage 7 — Eval runner**  
`uv run kivi eval --profiles off,exact,phonetic,llm`. Isolated DB per case. Compare vs `off`. Write `eval/results/latest.json` and `latest.md`. Missing LLM key → **SKIP** `llm` rows, do not fail others. Timeout/network on llm → SKIPPED/FAILED with reason, no hang.

**Stage 8 — LLM producer (optional path)**  
Glossary of **chosen** memories only. `temperature=0`, pinned model from `.env.example`, timeout. No call on ABSTAIN or profile `off`. Do not invent terms. Default path still works without a key.

**Stage 9 — README + RUN.md + dry run**  
Fill README: product, architecture, decisions, **limitations** (alignment degrades on heavy paraphrase; closed homophone list; phonetic short-token risk; cues fail if teach and run share no content words), AI use. RUN.md already has the 10 local items — make every command actually work. From a clean `uv sync`, seed, run the PDF example, eval, reset, repeat.

## Product reminder

Memory is a per-user lexical belief (canonical + observed forms + evidence + confidence). Observation ≠ memory. Retrieval ≠ apply. ABSTAIN is success. Three transcripts: ASR, formatted (input), memory-aware (output). You are not building STT.

PDF example after two teaches, `--profile exact`:

```
ASR:        ask aditya to review the sarvam kiwi service
formatted:  Ask Aditya to review the Sarvam Kiwi service.
memory:     Ask Aaditya to review the Sarvam Kivi service.
```

`--profile off` must equal formatted.

Start at Stage 1. When Stage 1 works, **ask me if you should commit** before Stage 2.
