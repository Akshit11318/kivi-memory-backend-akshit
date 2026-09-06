"""Profiles, paths, env. plan.md: config."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
DATA_DIR = REPO_ROOT / "data"
SEED_PATH = DATA_DIR / "seed" / "observations.json"
DEFAULT_DB_PATH = DATA_DIR / "kivi.sqlite"
EVAL_CASES_DIR = REPO_ROOT / "eval" / "cases"
EVAL_RESULTS_DIR = REPO_ROOT / "eval" / "results"
SCHEMA_PATH = PACKAGE_DIR / "store" / "schema.sql"

DEFAULT_USER_ID = "demo"
PROFILES = ("off", "exact", "phonetic", "llm")
DEFAULT_PROFILE = "exact"

APPLY_THRESHOLD = 0.75
DICTIONARY_ADD_CONFIDENCE = 1.0
FIRST_CORRECTION_CONFIDENCE = 0.85
CORRECTION_BUMP = 0.05
SEEDED_WEAK_CONFIDENCE = 0.40
SEEDED_BELOW_THRESHOLD = 0.60
