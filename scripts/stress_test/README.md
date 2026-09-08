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
  `kivi --profile auto run --json` CLI, and reports every metric: hits
  (TP/FP/FN, precision/recall), corrections applied, latency
  (sum/mean/median/p95/max/wall clock), model calls, token usage
  (prompt/completion), and an estimated cost.
- `results/latest.{json,md}` — the committed **ungated** (no key, free,
  deterministic) baseline. Regenerate with `run_stress_test.py` any time;
  a **gated** run with a real key produces different, non-deterministic
  numbers and is intentionally not committed — run it yourself.

## Running it

```
uv run python scripts/stress_test/generate_corpus.py   # regenerate the corpus (optional, already committed)
uv run python scripts/stress_test/run_stress_test.py               # ungated, free, deterministic
KIVI_LLM_API_KEY=... uv run python scripts/stress_test/run_stress_test.py            # gated, real cost
KIVI_LLM_API_KEY=... uv run python scripts/stress_test/run_stress_test.py --limit 20 # smoke test a subset first
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
Haiku key): precision recovers sharply once the LLM sense-check is in
the loop — **27 TP, 0 FP, 2 FN → precision 1.000, recall 0.931** on that
subset, at a real, measured cost of **~$0.046 for 20 paragraphs**
(`prompt_tokens=18094, completion_tokens=5509`), projecting to roughly
**$0.42 and ~15 minutes wall clock for the full 183-paragraph corpus**
sequentially. Multiple *distinct* ambiguous terms in one paragraph make
sequential calls (only *repeats of the same term* are batched — see
`decide/llm_helper.py`), which is why per-paragraph latency varies a lot
(observed mean ~4.7s, max ~8.8s on that subset).

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
