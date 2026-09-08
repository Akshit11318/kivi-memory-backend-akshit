"""MemoryStore: SQLite migrate, read/write, reset.

Learning writes this store. Inference only reads it.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from kivi_memory.config import SCHEMA_PATH
from kivi_memory.domain.models import Memory, Observation


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    def migrate(self) -> None:
        with self._conn:
            self._conn.executescript(SCHEMA_PATH.read_text())
            self._add_column_if_missing("memories", "teach_text", "TEXT")
            self._drop_column_if_present("memories", "context_cues")

    def _table_columns(self, table: str) -> set[str]:
        return {row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})")}

    def _add_column_if_missing(self, table: str, column: str, decl: str) -> None:
        if column not in self._table_columns(table):
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

    def _drop_column_if_present(self, table: str, column: str) -> None:
        """Best-effort: DROP COLUMN needs SQLite 3.35+. Older SQLite leaves the
        column in place, unused — the live code never reads it either way."""
        if column not in self._table_columns(table):
            return
        try:
            self._conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
        except sqlite3.OperationalError:
            pass

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def reset(self) -> None:
        """Wipe all rows. Schema stays. After this, list_memories() is empty."""
        with self._conn:
            self._conn.execute("DELETE FROM memory_forms")
            self._conn.execute("DELETE FROM observations")
            self._conn.execute("DELETE FROM memories")
            tables = {
                row["name"]
                for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            if "sqlite_sequence" in tables:
                self._conn.execute(
                    "DELETE FROM sqlite_sequence WHERE name IN ('memories', 'memory_forms', 'observations')"
                )

    # -- memories ----------------------------------------------------------

    def get_memory(self, memory_id: int) -> Memory | None:
        row = self._conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return self._row_to_memory(row) if row else None

    def get_memory_by_canonical(self, user_id: str, canonical: str) -> Memory | None:
        row = self._conn.execute(
            "SELECT * FROM memories WHERE user_id = ? AND canonical = ?",
            (user_id, canonical),
        ).fetchone()
        return self._row_to_memory(row) if row else None

    def find_memory_ids_by_form(self, user_id: str, form: str) -> list[int]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT m.id FROM memories m
            JOIN memory_forms f ON f.memory_id = m.id
            WHERE m.user_id = ? AND f.form = ?
            ORDER BY m.id
            """,
            (user_id, form),
        ).fetchall()
        return [row["id"] for row in rows]

    def list_memories(self, user_id: str | None = None) -> list[Memory]:
        if user_id is None:
            rows = self._conn.execute("SELECT * FROM memories ORDER BY id").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
        return [self._row_to_memory(row) for row in rows]

    def upsert_memory(
        self,
        user_id: str,
        canonical: str,
        forms: Iterable[str],
        confidence: float,
        teach_text: str | None = None,
    ) -> Memory:
        """Same (user_id, canonical) -> merge: union forms, replace confidence.

        Caller (the learner) computes the confidence to write — this method does
        not apply the 0.85/+0.05/cap-1.0 policy itself. `teach_text` is evidence
        for the LLM sense helper's prompt only, never a gate: a later call that
        passes None keeps whatever teach_text is already stored; a later call
        that passes a sentence replaces it with the newer evidence.
        """
        now = utc_now()
        deduped_forms = tuple(dict.fromkeys(forms))
        existing = self.get_memory_by_canonical(user_id, canonical)
        with self._conn:
            if existing is None:
                cursor = self._conn.execute(
                    "INSERT INTO memories(user_id, canonical, confidence, teach_text, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, canonical, confidence, teach_text, now, now),
                )
                memory_id = cursor.lastrowid
            else:
                memory_id = existing.id
                merged_teach_text = teach_text if teach_text is not None else existing.teach_text
                self._conn.execute(
                    "UPDATE memories SET confidence = ?, teach_text = ?, updated_at = ? WHERE id = ?",
                    (confidence, merged_teach_text, now, memory_id),
                )
            for form in deduped_forms:
                self._conn.execute(
                    "INSERT OR IGNORE INTO memory_forms(memory_id, form) VALUES (?, ?)",
                    (memory_id, form),
                )
        memory = self.get_memory(memory_id)
        assert memory is not None
        return memory

    # -- observations --------------------------------------------------------

    def add_observation(self, observation: Observation) -> int:
        created_at = observation.created_at or utc_now()
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO observations"
                "(user_id, source, asr, formatted, final, canonical, forms, memory_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    observation.user_id,
                    observation.source,
                    observation.asr,
                    observation.formatted,
                    observation.final,
                    observation.canonical,
                    json.dumps(list(observation.forms)),
                    observation.memory_id,
                    created_at,
                ),
            )
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    def count_observations(self, user_id: str, canonical: str, source: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM observations WHERE user_id = ? AND canonical = ? AND source = ?",
            (user_id, canonical, source),
        ).fetchone()
        return int(row["n"])

    def list_observations(self, user_id: str | None = None) -> list[Observation]:
        if user_id is None:
            rows = self._conn.execute("SELECT * FROM observations ORDER BY id").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM observations WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
        return [self._row_to_observation(row) for row in rows]

    # -- row mapping ---------------------------------------------------------

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        forms = self._conn.execute(
            "SELECT form FROM memory_forms WHERE memory_id = ? ORDER BY id", (row["id"],)
        ).fetchall()
        return Memory(
            id=row["id"],
            user_id=row["user_id"],
            canonical=row["canonical"],
            forms=tuple(f["form"] for f in forms),
            confidence=row["confidence"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            teach_text=row["teach_text"],
        )

    def _row_to_observation(self, row: sqlite3.Row) -> Observation:
        return Observation(
            id=row["id"],
            user_id=row["user_id"],
            source=row["source"],
            asr=row["asr"],
            formatted=row["formatted"],
            final=row["final"],
            canonical=row["canonical"],
            forms=tuple(json.loads(row["forms"])) if row["forms"] else (),
            memory_id=row["memory_id"],
            created_at=row["created_at"],
        )
