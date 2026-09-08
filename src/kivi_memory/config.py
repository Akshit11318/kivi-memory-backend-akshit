"""Profiles, paths, thresholds, LLM sense-helper env names."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
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
DEFAULT_LLM_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_LLM_MODEL = "mistralai/mistral-small-3.2-24b-instruct:free"
LLM_TIMEOUT_SECONDS = 15.0
LLM_TEMPERATURE = 0
