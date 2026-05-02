"""Local chat session storage for iterative training and app development.

Supports two backends:
* ``jsonl`` (default) – append-only JSONL file, zero extra dependencies.
* ``sqlite``          – SQLite database, survives concurrent writers and
  large session counts much better than the flat-file approach.

The backend is selected via ``settings.CHAT_STORE_BACKEND``.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass
class ChatTurn:
    """Single chat exchange stored for local training artifacts."""

    timestamp: str
    session_id: str
    user_query: str
    answer: str
    intent: str
    citations: list[dict[str, Any]]
    metadata: dict[str, Any]
    # New fields for learning integration
    feedback: dict[str, Any] | None = None  # e.g. {"type":"verified","text":...}
    learning_event_id: str | None = None
    confidence_before: float | None = None
    confidence_after: float | None = None


# ---------------------------------------------------------------------------
# JSONL backend (original, kept for backwards compatibility)
# ---------------------------------------------------------------------------

class _JsonlStore:
    """Append-only JSONL store for chat exchanges."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append_turn(self, turn: ChatTurn) -> None:
        with self._lock:
            with self.file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(turn.__dict__, ensure_ascii=False) + "\n")

    def list_session(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("session_id") == session_id:
                    rows.append(row)
        return rows[-limit:]

    def export_session_jsonl(self, session_id: str) -> str:
        rows = self.list_session(session_id=session_id, limit=10_000)
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)


# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS chat_turns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    session_id  TEXT    NOT NULL,
    user_query  TEXT    NOT NULL,
    answer      TEXT    NOT NULL,
    intent      TEXT    NOT NULL,
    citations   TEXT    NOT NULL,
    metadata    TEXT    NOT NULL,
    feedback    TEXT,
    learning_event_id TEXT,
    confidence_before REAL,
    confidence_after REAL
);
CREATE INDEX IF NOT EXISTS idx_session_id ON chat_turns (session_id);
"""


class _SqliteStore:
    """SQLite-backed chat turn store."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(_CREATE_TABLE)
                conn.commit()
            finally:
                conn.close()

    def append_turn(self, turn: ChatTurn) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO chat_turns "
                    "(timestamp, session_id, user_query, answer, intent, citations, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        turn.timestamp,
                        turn.session_id,
                        turn.user_query,
                        turn.answer,
                        turn.intent,
                        json.dumps(turn.citations, ensure_ascii=False),
                        json.dumps(turn.metadata, ensure_ascii=False),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list_session(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM chat_turns WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            )
            rows = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
        # Deserialise JSON fields and reverse to chronological order
        for row in rows:
            try:
                row["citations"] = json.loads(row["citations"])
            except Exception:
                row["citations"] = []
            try:
                row["metadata"] = json.loads(row["metadata"])
            except Exception:
                row["metadata"] = {}
        rows.reverse()
        return rows

    def export_session_jsonl(self, session_id: str) -> str:
        rows = self.list_session(session_id=session_id, limit=10_000)
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)


# ---------------------------------------------------------------------------
# Public façade – delegates to the configured backend
# ---------------------------------------------------------------------------

class LocalTrainingStore:
    """Chat turn store that delegates to JSONL or SQLite based on settings."""

    def __init__(
        self,
        file_path: str | Path | None = None,
        db_path: str | Path | None = None,
        backend: str | None = None,
    ) -> None:
        from lios.config import settings as _settings

        _backend = (backend or _settings.CHAT_STORE_BACKEND).lower()
        if _backend == "sqlite":
            _db_path = db_path or _settings.CHAT_STORE_DB_PATH
            self._store: _JsonlStore | _SqliteStore = _SqliteStore(_db_path)
        else:
            _file = file_path or _settings.CHAT_STORE_PATH
            self._store = _JsonlStore(_file)

    # ------------------------------------------------------------------
    # Delegate to backend
    # ------------------------------------------------------------------

    def append_turn(self, turn: ChatTurn) -> None:
        self._store.append_turn(turn)

    def list_session(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self._store.list_session(session_id, limit)

    def export_session_jsonl(self, session_id: str) -> str:
        return self._store.export_session_jsonl(session_id)

    # ------------------------------------------------------------------
    # Session direction inference (unchanged from original)
    # ------------------------------------------------------------------

    def infer_session_direction(self, session_id: str, window: int = 3) -> dict[str, Any] | None:
        """Infer stable session direction from the latest turns."""
        if window < 2:
            window = 2

        rows = self.list_session(session_id=session_id, limit=window)
        if len(rows) < window:
            return None

        intents = [r.get("intent") for r in rows if r.get("intent")]
        intent_hint: str | None = None
        intent_confidence = 0.0
        if intents:
            intent_counts: dict[str, int] = {}
            for intent in intents:
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
            intent_hint, max_count = max(intent_counts.items(), key=lambda item: item[1])
            intent_confidence = max_count / len(rows)
            if intent_confidence < 0.67:
                intent_hint = None

        reg_counts: dict[str, int] = {}
        for row in rows:
            for citation in row.get("citations") or []:
                reg = citation.get("regulation")
                if reg:
                    reg_counts[reg] = reg_counts.get(reg, 0) + 1

        regulation_hint: str | None = None
        regulation_confidence = 0.0
        if reg_counts:
            regulation_hint, reg_count = max(reg_counts.items(), key=lambda item: item[1])
            regulation_confidence = reg_count / max(1, sum(reg_counts.values()))
            if regulation_confidence < 0.5:
                regulation_hint = None

        if intent_hint is None and regulation_hint is None:
            return None

        return {
            "intent": intent_hint,
            "regulation": regulation_hint,
            "intent_confidence": round(intent_confidence, 3),
            "regulation_confidence": round(regulation_confidence, 3),
            "window": len(rows),
        }

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

