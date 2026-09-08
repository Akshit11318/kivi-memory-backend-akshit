"""Profiles, paths, thresholds, LLM sense-helper env names."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]


def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE from path into os.environ if the key is not already set.

    Does not override a real export (pytest monkeypatch, CI, `export`). Missing
    file is a no-op. No extra dependency.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(REPO_ROOT / ".env")
DATA_DIR = REPO_ROOT / "data"
SEED_PATH = DATA_DIR / "seed" / "observations.json"
DEFAULT_DB_PATH = DATA_DIR / "kivi.sqlite"
EVAL_DATASET_DIR = REPO_ROOT / "eval" / "dataset"
EVAL_RESULTS_DIR = REPO_ROOT / "eval" / "results"
SCHEMA_PATH = PACKAGE_DIR / "store" / "schema.sql"

DEFAULT_USER_ID = "demo"
# "auto" cascades exact -> phonetic and is the default live path. "exact" and
# "phonetic" force a single retriever for ablation but run the same decide.
PROFILES = ("off", "exact", "phonetic", "auto")
DEFAULT_PROFILE = "auto"

APPLY_THRESHOLD = 0.75
DICTIONARY_ADD_CONFIDENCE = 1.0
FIRST_CORRECTION_CONFIDENCE = 0.85
CORRECTION_BUMP = 0.05
SEEDED_WEAK_CONFIDENCE = 0.40
SEEDED_BELOW_THRESHOLD = 0.60

# LLM sense helper (decide/llm_helper.py) — last vote for APPLY vs ABSTAIN.
# No key -> ungated APPLY after the cheap doors. Never a cue fallback.
LLM_API_KEY_ENV = "KIVI_LLM_API_KEY"
LLM_BASE_URL_ENV = "KIVI_LLM_BASE_URL"
LLM_MODEL_ENV = "KIVI_LLM_MODEL"
DEFAULT_LLM_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_LLM_MODEL = "claude-haiku-4-5-20251001"
LLM_TIMEOUT_SECONDS = 15.0
LLM_TEMPERATURE = 0
# The LLM scores sense-match 0-100 per occurrence (a repeated token in one
# sentence is batched into one call, not one call per occurrence -- see
# decide/llm_helper.py). Each score is blended with the memory's own
# confidence (evidence this is a real taught spelling at all, independent of
# sense) as a product -- weak evidence on either axis pulls the combined
# value down. combined = memory.confidence * (score / 100); APPLY iff
# combined >= this threshold.
LLM_COMBINED_APPLY_THRESHOLD = 0.5
