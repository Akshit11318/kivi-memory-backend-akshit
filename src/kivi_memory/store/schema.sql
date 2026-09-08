-- V002. observations, memories, memory_forms, meta. Reset must wipe rows, keep schema.
-- V002 drops context_cues (the cue gate is deleted) and adds teach_text
-- (LLM-prompt evidence only, never a gate). MemoryStore.migrate() applies
-- that column change to already-existing databases at open time.

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', '2');

-- One memory = one per-user lexical belief: canonical spelling + confidence.
-- teach_text: the correction sentence, or an optional dictionary_add example
-- sentence, kept solely as evidence for the LLM sense helper's prompt.
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    canonical TEXT NOT NULL,
    confidence REAL NOT NULL,
    teach_text TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, canonical)
);

-- Observed surface forms for a memory (includes the normalized canonical-as-form,
-- so conflict detection can find two canonicals sharing one surface).
CREATE TABLE IF NOT EXISTS memory_forms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    form TEXT NOT NULL,
    UNIQUE (memory_id, form)
);

CREATE INDEX IF NOT EXISTS idx_memory_forms_form ON memory_forms(form);

-- Raw teach events. memory_id is set once an observation results in a memory
-- upsert — pointer to the observation that created or reinforced the row.
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    source TEXT NOT NULL,
    asr TEXT,
    formatted TEXT,
    final TEXT,
    canonical TEXT,
    forms TEXT,
    memory_id INTEGER REFERENCES memories(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observations_user ON observations(user_id);
