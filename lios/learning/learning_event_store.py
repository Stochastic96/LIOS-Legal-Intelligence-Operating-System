"""Learning event storage system.

Stores:
- Feedback events (user validation/correction/instruction)
- Learning milestones (when topics reach new levels)
- Verified answers (high-confidence knowledge)
- Corrections (what LIOS got wrong and right)

All events are append-only and version-controlled.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from lios.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class LearningEvent:
    """A single learning event (feedback, milestone, correction, etc)."""

    timestamp: str  # ISO 8601
    session_id: str
    event_type: str  # "feedback", "correction", "verified_answer", "milestone"
    topic: Optional[str]
    content: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "topic": self.topic,
            "content": self.content,
        }


class LearningEventStore:
    """SQLite-backed store for learning events."""

    def __init__(self, db_path: str | Path = "logs/learning_events.db") -> None:
        """Initialize learning event store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS learning_events (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp       TEXT NOT NULL,
                        session_id      TEXT NOT NULL,
                        event_type      TEXT NOT NULL,
                        topic           TEXT,
                        content         TEXT NOT NULL
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_session ON learning_events (session_id);
                    CREATE INDEX IF NOT EXISTS idx_topic ON learning_events (topic);
                    CREATE INDEX IF NOT EXISTS idx_type ON learning_events (event_type);
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON learning_events (timestamp);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def append_event(self, event: LearningEvent) -> str:
        """Append a learning event.
        
        Args:
            event: LearningEvent to store
            
        Returns:
            Event ID
        """
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """
                    INSERT INTO learning_events
                    (timestamp, session_id, event_type, topic, content)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.timestamp,
                        event.session_id,
                        event.event_type,
                        event.topic,
                        json.dumps(event.content, ensure_ascii=False),
                    ),
                )
                conn.commit()
                event_id = str(cur.lastrowid)
                logger.debug(f"Stored learning event {event_id}: {event.event_type}")
                return event_id
            finally:
                conn.close()

    def append_feedback_event(self, feedback_event: Any) -> str:
        """Store a feedback event (from FeedbackHandler).
        
        Args:
            feedback_event: FeedbackEvent from feedback_handler.py
            
        Returns:
            Event ID
        """
        event = LearningEvent(
            timestamp=feedback_event.timestamp,
            session_id=feedback_event.session_id,
            event_type="feedback",
            topic=None,  # Could extract from query
            content=feedback_event.to_dict(),
        )
        return self.append_event(event)

    def record_verified_answer(
        self,
        query: str,
        answer: str,
        session_id: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """Record a verified (correct) answer.
        
        Args:
            query: The question
            answer: The verified correct answer
            session_id: Session ID
            timestamp: Optional override timestamp
            
        Returns:
            Event ID
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        event = LearningEvent(
            timestamp=ts,
            session_id=session_id,
            event_type="verified_answer",
            topic=None,
            content={
                "query": query,
                "answer": answer,
                "confidence": 1.0,
                "source": "user_verification",
            },
        )
        return self.append_event(event)

    def record_correction(
        self,
        original_query: str,
        incorrect_answer: str,
        correction: str,
        session_id: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """Record a correction (what LIOS got wrong and right).
        
        Args:
            original_query: The question that was answered wrong
            incorrect_answer: What LIOS said (wrong)
            correction: What is actually correct
            session_id: Session ID
            timestamp: Optional override timestamp
            
        Returns:
            Event ID
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        event = LearningEvent(
            timestamp=ts,
            session_id=session_id,
            event_type="correction",
            topic=None,
            content={
                "query": original_query,
                "wrong": incorrect_answer,
                "correct": correction,
                "source": "user_correction",
            },
        )
        return self.append_event(event)

    def record_partial_feedback(
        self,
        query: str,
        answer: str,
        missing: str,
        session_id: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """Record partial feedback (answer is right direction but incomplete).
        
        Args:
            query: The question
            answer: LIOS's partial answer
            missing: What was missing or incomplete
            session_id: Session ID
            timestamp: Optional override timestamp
            
        Returns:
            Event ID
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        event = LearningEvent(
            timestamp=ts,
            session_id=session_id,
            event_type="partial_feedback",
            topic=None,
            content={
                "query": query,
                "answer": answer,
                "missing": missing,
                "source": "user_feedback",
            },
        )
        return self.append_event(event)

    def record_instruction(
        self,
        instruction: str,
        context: str,
        session_id: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """Record an instruction (teaching LIOS a new rule).
        
        Args:
            instruction: The rule to remember
            context: Context where this rule applies
            session_id: Session ID
            timestamp: Optional override timestamp
            
        Returns:
            Event ID
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        event = LearningEvent(
            timestamp=ts,
            session_id=session_id,
            event_type="instruction",
            topic=None,
            content={
                "instruction": instruction,
                "context": context,
                "source": "user_instruction",
            },
        )
        return self.append_event(event)

    def bookmark_answer(
        self, query: str, answer: str, session_id: str
    ) -> str:
        """Bookmark an answer for later review/study.
        
        Args:
            query: The question
            answer: The answer to bookmark
            session_id: Session ID
            
        Returns:
            Event ID
        """
        event = LearningEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            event_type="bookmark",
            topic=None,
            content={
                "query": query,
                "answer": answer,
                "for_review": True,
            },
        )
        return self.append_event(event)

    def queue_deeper_explanation(self, query: str, original_answer: str) -> str:
        """Queue a request for deeper explanation.
        
        Args:
            query: The original question
            original_answer: The brief answer given
            
        Returns:
            Event ID
        """
        event = LearningEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id="system",  # Not tied to a session
            event_type="deepening_request",
            topic=None,
            content={
                "query": query,
                "brief_answer": original_answer,
                "needs_expansion": True,
            },
        )
        return self.append_event(event)

    def get_session_feedback(self, session_id: str) -> list[dict[str, Any]]:
        """Get all feedback events from a session.
        
        Args:
            session_id: Session ID to query
            
        Returns:
            List of feedback event dicts
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT * FROM learning_events
                WHERE session_id = ? AND event_type = 'feedback'
                ORDER BY timestamp ASC
                """,
                (session_id,),
            )
            rows = [dict(row) for row in cur.fetchall()]
            for row in rows:
                row["content"] = json.loads(row["content"])
            return rows
        finally:
            conn.close()

    def get_corrections_for_topic(self, topic: str) -> list[dict[str, Any]]:
        """Get all corrections related to a topic.
        
        Args:
            topic: Topic name
            
        Returns:
            List of correction event dicts
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT * FROM learning_events
                WHERE (topic = ? OR content LIKE ?)
                  AND event_type IN ('correction', 'partial_feedback')
                ORDER BY timestamp DESC
                """,
                (topic, f"%{topic}%"),
            )
            rows = [dict(row) for row in cur.fetchall()]
            for row in rows:
                row["content"] = json.loads(row["content"])
            return rows
        finally:
            conn.close()

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """Get summary of a session's learning events.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dictionary with event counts and summary
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM learning_events
                WHERE session_id = ?
                GROUP BY event_type
                """,
                (session_id,),
            )
            summary: dict[str, Any] = {
                "session_id": session_id,
                "event_counts": {},
            }

            for row in cur.fetchall():
                summary["event_counts"][row["event_type"]] = row["count"]

            return summary
        finally:
            conn.close()

    def export_session_jsonl(self, session_id: str) -> str:
        """Export a session's learning events as JSONL.
        
        Args:
            session_id: Session ID
            
        Returns:
            JSONL string (one JSON object per line)
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT * FROM learning_events
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,),
            )

            lines = []
            for row in cur.fetchall():
                obj = dict(row)
                obj["content"] = json.loads(obj["content"])
                # Remove the id field
                obj.pop("id", None)
                lines.append(json.dumps(obj, ensure_ascii=False))

            return "\n".join(lines)
        finally:
            conn.close()
