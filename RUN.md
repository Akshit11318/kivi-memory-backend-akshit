Completely local application. Python 3.13+ via uv. SQLite file on disk.
Default profile (`exact`) needs no environment variables. Optional
`KIVI_LLM_API_KEY` / `KIVI_LLM_MODEL` enable the `llm` profile.
No hosted URL.

## 1. Runtimes

- Python 3.13+
- uv 0.4+

## 2. Environment variables

None required. Optional: see `.env.example`.

## 3. Install

```
uv sync
```

## 4. Create, migrate, seed

```
uv run kivi reset --seed
```

(Not implemented in the backbone yet.)

## 5. Start

No daemon. The CLI is the process:

```
uv run kivi --help
```

## 6. Interface

Terminal. No URL.

## 7. Primary interactions

`observe`, `memories`, `run`, `eval`, `reset` — implement per plan.md.

## 8. Evaluation

```
uv run kivi eval --profiles off,exact,phonetic,llm
```

## 9. Results location

`eval/results/latest.json` and `eval/results/latest.md`

## 10. Reset

```
uv run kivi reset
uv run kivi reset --seed
```
