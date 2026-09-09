# Eval dataset

Two flat CSVs, no JSON tree. `kivi eval` reads these and only these.

- `teaches.csv` — setup. `case_id` ties a row (or ordered `step` sequence of
  rows) to a case in `cases.csv`. Replayed into a fresh, isolated SQLite file
  before that case runs. `source` is `dictionary_add` or `correction`, the
  same two learner entry points `kivi observe` uses. `forms` is
  `|`-separated. `teach_text` is only meaningful on a `dictionary_add` row —
  a `correction` row's `teach_text` is set automatically to its `final`
  sentence by the learner.
- `cases.csv` — one row is one (scenario, profile) run. `profile` is a column,
  not a sweep flag: two rows with the same underlying teach but different
  `profile` values is how the exact-vs-auto and ablation comparisons work.
  `expected_hits` is a JSON list of `{"from": ..., "to": ...}` pairs — the
  literal (token, canonical) pairs a correct APPLY should produce, matched as
  a multiset so repeated mentions each count. `[]` means a deliberate no-op:
  the row asserts nothing rewrites. `expected_memory_aware`, if set, is
  checked as an exact string match on top of the hit count.

## Hit scoring

`expected_hit`: a `from -> to` pair asserted by the case. `actual_hit`: a
token the system actually replaced via APPLY. Per row: TP = hits that match,
FP = an APPLY the case didn't expect, FN = an expected hit the system didn't
produce. Precision/recall are TP over (TP+FP) / (TP+FN), aggregated per
`profile` and overall. The headline is these numbers, not a pass count —
a suite can have 100% "cases passed" while quietly missing every real hit if
hits aren't scored separately from string equality.

## `requires_llm`

A row with `requires_llm=true` asserts the LLM sense helper's judgment
(e.g. fruit vs brand). It is **SKIPPED**, not scored, under
`--decide ungated` — scoring it against ungated APPLY would assert a
decision the run never attempted. `kivi eval` (default `--decide llm`)
requires `KIVI_LLM_API_KEY` and `KIVI_LLM_MODEL` and makes real HTTP calls
for these rows (unlike `pytest`, which mocks
`decide.llm_helper._post_chat_completion` and never hits the network).

**The committed `eval/results/latest.{json,md}` is the `--decide ungated`
snapshot** — deterministic, reproducible, and what's graded. The report
includes a Time section (median / mean / p95 / max / sum). Headline
numbers are in README [Metrics](../../README.md#metrics).

## Case intent, by family

- **alignment** (`akshit_paragraph`, `akshit_contraction`) — `SequenceMatcher`
  alignment, not positional index: a formatter contraction expansion
  (`gonna` -> `going to`) must not corrupt neighboring tokens.
- **off_control** (`akshit_off`) — `--profile off` is a passthrough: 0 hits,
  text byte-identical to the input.
- **retrieve_cascade** (`graffana_exact`, `graffana_auto`,
  `phonetic_grafana_zeroshot`) — the same input under `exact` (FN — the
  stored form is `grafana`, not `graffana`) vs `auto` and `phonetic` (TP —
  the cascade falls through to Metaphone). Proves the two retrievers are not
  redundant.
- **multi_entity** (`two_names_paragraph`, `multi_mention`) — two names in
  one paragraph, and one name mentioned three times in one sentence; every
  mention must independently APPLY.
- **deliberate_noop** (`noop_paragraph`) — a paragraph that shares no
  vocabulary with the notebook. The right answer is doing nothing.
- **conflicting_canonicals** (`riya_ria_conflict`, `conflicting_two_people`)
  — two rows claim the same surface. ABSTAIN, never rank by confidence.
- **llm_sense** (`kiwi_fruit_abstain`, `kiwi_staging_apply`,
  `groww_grow_abstain`, `groww_grow_apply`) — the cases that need a real
  sense judgment, not lexical overlap. `kiwi_staging_apply` in particular
  shares no neighbor words with the teach sentence at all — the deleted cue
  gate could never have applied it; the LLM does, from sense alone.
- **documented_limitation** (`karan_karen_limitation`,
  `sanjay_sanjeev_limitation`) — misfires we did not hide. Both APPLY under
  the ungated path (`--decide ungated`): a Metaphone collision (`Karan`/`Karen`) and a
  grapheme-similar different person (`Sanjay`/`Sanjeev`). Speaker identity is
  out of scope for this system; see README Limitations.
- **cheap_doors** (`already_canonical`, `word_boundary`) — a token that
  already is the canonical needs no rewrite; a substring match
  (`Kivi` inside `Kivimaki`) is not a match at all.
- **tokenize** (`possessive_clitic`, `hyphen_segment`, `punct_quoted_token`,
  `stylized_lowercase_apply`) — punctuation, possessives, hyphen segments,
  and quotes must stitch back losslessly around the rewritten core.
- **isolation** (`multi_user_isolation`) — one user's memory must not leak
  into another user's run.
- **learner_refuse** (`learner_refuse_grammar`, `learner_refuse_content`) —
  `there`/`their` and `Friday`/`Thursday` teach **zero** memory rows; running
  the same sentence afterward is still a no-op.
- **formatter_regression** (`formatter_regressed_name`,
  `formatter_regressed_brand`) — the formatter can regress a name or brand to
  a known non-canonical spelling; `decide` reads the *formatted* token, so it
  can undo that regression.
- **phonetic_guard** (`ravi_robbie_no_fp`, `kavi_covey_no_fp`) — short-token
  phonetic collisions that must **not** fire, guarded by the Metaphone code
  itself and the first-letter check.
- **phonetic_only** (`brand_dropped_vowel_zeroshot`) — a dropped-vowel
  misspelling (`Flikr`/`Flickr`) that only the phonetic retriever reaches.
- **exact_retrieval** (`bengali_surname_variant`) — a pre-registered
  alternate spelling that `exact` alone resolves, no phonetic needed.
- **learner_merge** (`merge_dictionary_forms`) — two `dictionary_add` calls
  on the same canonical merge forms into one row instead of duplicating it.
- **code_switch** (`hinglish_code_switch`) — a name inside a code-switched
  (Hindi/English) sentence still gets found and applied.
- **robustness** (`empty_garbage_input`) — empty input does not crash and
  produces no hits.
