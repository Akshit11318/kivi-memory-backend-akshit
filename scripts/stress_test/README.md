# Stress test: a large, partially-taught corpus with full metrics

A stress test distinct from `eval/dataset/` — larger (10,500+ words, 183
paragraphs), synthetic, and deliberately confusing: 58 vocabulary items
across three categories (pure name respellings, brand/common-word
homographs with a real spelling variant, and phonetic-only technical
terms), only 60% of which are taught before the corpus runs. The corpus
mixes taught and untaught vocabulary, and — for homographs — the same
word used in the taught sense and its ordinary dictionary sense, so both
precision (false positives on the wrong sense) and recall (missed correct
senses, missed untaught-vocabulary no-ops) are measurable at scale.

## Files

- `generate_corpus.py` — deterministic generator (fixed seed). Produces:
  - `corpus.txt` — one paragraph per line
  - `ground_truth.json` — per-paragraph expected hits (`{"from", "to"}`)
  - `teaches.json` — the partial (60%) set of `dictionary_add` observations
  - `vocab_manifest.json` — which vocabulary was taught vs. left untaught
- `run_stress_test.py` — replays `teaches.json` into an isolated SQLite
  (`stress.sqlite`, gitignored), runs every paragraph through the real
  `kivi --profile auto --decide … run --json` CLI, and writes a report in
  plain terms: last vote (sense check vs skip model), rewrites (found /
  extra / missed), time, HTTP calls, and estimated cost.
- `results/latest.{json,md}` — summary metrics. `latest.cases.csv` is the
  paragraph table (formatted / expected / kivi / what changed). The committed
  snapshot is **`--decide ungated`**. A **sense-check** run (`--decide llm`)
  overwrites these locally and is not committed.

## Running it

```
uv run python scripts/stress_test/generate_corpus.py   # regenerate the corpus (optional, already committed)
uv run python scripts/stress_test/run_stress_test.py --limit 10              # ungated latency
uv run python scripts/stress_test/run_stress_test.py --decide ungated         # full ungated
uv run python scripts/stress_test/run_stress_test.py --decide llm --limit 10  # gated, needs key+model
```

## What to expect

**Ungated** (committed baseline): every taught vocabulary item that
clears the cheap doors APPLYs with no sense check — recall is perfect
(every taught, correct-sense mention gets corrected) but precision takes
a real hit from homographs used in their *ordinary* sense (e.g. "he
always orders `mint` chocolate chip" incorrectly becomes "`Mintt`
chocolate chip"). Measured: **240/240 expected hits found (recall
1.000), but 141 false positives → precision 0.630** across all 183
paragraphs.

**Gated** (smoke-tested on the first 20 paragraphs with a real Claude
Haiku key): precision recovers once the sense check is in the loop —
**27 TP, 0 FP, 2 FN → precision 1.000, recall 0.931** on that subset, at
a measured **~$0.046** (`prompt_tokens=18094, completion_tokens=5509`).
Current code is **one HTTP call per paragraph** that still has a
survivor (all memories in that string, together) — not one call per
distinct term. A full 183-paragraph gated run is at most 183 calls, not
one per word. Do not overwrite the committed ungated snapshot with a
gated run.

`PRICING_PER_MILLION_TOKENS` in `run_stress_test.py` is a rough estimate
— verify against current provider pricing before treating the $ figure
as authoritative.

## Design note: why every homograph canonical is stylized, not a case difference

A homograph pair whose canonical is *only* a capitalization of the
ordinary word (e.g. canonical `Notion`, form `notion`) can never reach
the LLM sense-check at all: `decide/conservative.py`'s `already_canonical`
door fires on any case-insensitive match regardless of sense, by design
(case belongs to the formatter, not a correction). That's correct
behavior, but it means such a pair can't demonstrate the sense-check
either way. Every homograph here (`Notionn`/notion, `Slackk`/slack,
`Groww`/grow, `Kivi`/kiwi, ...) has a genuine one-letter spelling
difference from the ordinary word, so retrieval finds it but
`already_canonical` doesn't short-circuit it — the LLM helper actually
gets exercised.
