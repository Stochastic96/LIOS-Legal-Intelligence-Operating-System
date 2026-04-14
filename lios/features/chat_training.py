"""Local chat session storage for iterative training and app development."""

from __future__ import annotations

import json
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


class LocalTrainingStore:
    """Append-only JSONL store for chat exchanges."""

    def __init__(self, file_path: str | Path = "logs/chat_training.jsonl") -> None:
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
        session_rows = self.list_session(session_id=session_id, limit=10_000)
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in session_rows)

    def infer_session_direction(self, session_id: str, window: int = 3) -> dict[str, Any] | None:
        """Infer stable session direction from the latest turns.

        Returns a directional hint when recent turns show a clear intent and/or regulation trend.
        """
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
