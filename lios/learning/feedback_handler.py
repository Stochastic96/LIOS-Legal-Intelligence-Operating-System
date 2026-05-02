"""Feedback handling system for LIOS learning mode.

Processes user feedback on answers:
- ✅ Good / ⭐ Verified
- ❌ Wrong / incorrect answer
- ⚠️ Partial / needs more work
- 📝 Instruct / teach LIOS a new rule

All feedback is stored as training data and updates knowledge base confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import json


class FeedbackType(str, Enum):
    """Types of feedback user can provide."""

    VERIFIED = "verified"  # ✅ This answer is correct, store as verified
    WRONG = "wrong"  # ❌ This answer is wrong, here's the correction
    PARTIAL = "partial"  # ⚠️ Right direction but missing something
    INSTRUCT = "instruct"  # 📝 Teach me a new rule
    SAVE = "save"  # ⭐ Bookmark this answer for later
    DEEPER = "deeper"  # 📚 I want more detail on this


@dataclass
class FeedbackEvent:
    """A feedback event from a user about a LIOS answer."""

    session_id: str
    timestamp: str  # ISO 8601
    user_id: Optional[str]  # Optional: who gave the feedback
    
    query: str  # Original question
    answer: str  # LIOS's answer being evaluated
    
    feedback_type: FeedbackType
    feedback_text: Optional[str] = None  # For WRONG/INSTRUCT/PARTIAL feedback
    
    answer_id: Optional[str] = None  # Reference to stored answer
    confidence_before: Optional[float] = None  # LIOS confidence before feedback
    
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        session_id: str,
        query: str,
        answer: str,
        feedback_type: FeedbackType,
        feedback_text: Optional[str] = None,
        user_id: Optional[str] = None,
        **extra_metadata,
    ) -> FeedbackEvent:
        """Create a new feedback event with current timestamp."""
        return cls(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
            query=query,
            answer=answer,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            metadata=extra_metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "query": self.query,
            "answer": self.answer,
            "feedback_type": self.feedback_type.value,
            "feedback_text": self.feedback_text,
            "answer_id": self.answer_id,
            "confidence_before": self.confidence_before,
            "metadata": self.metadata,
        }


class FeedbackHandler:
    """Process and store user feedback for learning."""

    def __init__(self, store: Any) -> None:
        """Initialize with a learning event store.
        
        Args:
            store: LearningEventStore instance for persisting feedback
        """
        self.store = store

    def process_feedback(self, event: FeedbackEvent) -> dict[str, Any]:
        """Process a feedback event and update knowledge base.
        
        Returns:
            Dictionary with processing results and next steps.
        """
        result: dict[str, Any] = {
            "status": "processed",
            "feedback_id": f"{event.session_id}:{event.timestamp}",
            "feedback_type": event.feedback_type.value,
            "actions_taken": [],
        }

        # Process by feedback type
        if event.feedback_type == FeedbackType.VERIFIED:
            result["actions_taken"].append("confident_answer_recorded")
            # LIOS stores this answer as high-confidence verified knowledge
            self.store.record_verified_answer(
                query=event.query,
                answer=event.answer,
                session_id=event.session_id,
                timestamp=event.timestamp,
            )

        elif event.feedback_type == FeedbackType.WRONG:
            result["actions_taken"].append("correction_recorded")
            # User is correcting LIOS
            if event.feedback_text:
                self.store.record_correction(
                    original_query=event.query,
                    incorrect_answer=event.answer,
                    correction=event.feedback_text,
                    session_id=event.session_id,
                    timestamp=event.timestamp,
                )
                result["correction_summary"] = (
                    f"Stored: '{event.answer}' is wrong. "
                    f"Correct: '{event.feedback_text}'"
                )

        elif event.feedback_type == FeedbackType.PARTIAL:
            result["actions_taken"].append("partial_feedback_recorded")
            if event.feedback_text:
                self.store.record_partial_feedback(
                    query=event.query,
                    answer=event.answer,
                    missing=event.feedback_text,
                    session_id=event.session_id,
                    timestamp=event.timestamp,
                )

        elif event.feedback_type == FeedbackType.INSTRUCT:
            result["actions_taken"].append("instruction_recorded")
            # User is giving LIOS a new rule
            if event.feedback_text:
                self.store.record_instruction(
                    instruction=event.feedback_text,
                    context=event.query,
                    session_id=event.session_id,
                    timestamp=event.timestamp,
                )
                result["instruction_summary"] = (
                    f"Learned new rule: {event.feedback_text}"
                )

        elif event.feedback_type == FeedbackType.SAVE:
            result["actions_taken"].append("answer_bookmarked")
            self.store.bookmark_answer(
                query=event.query,
                answer=event.answer,
                session_id=event.session_id,
            )

        elif event.feedback_type == FeedbackType.DEEPER:
            result["actions_taken"].append("deepening_queued")
            self.store.queue_deeper_explanation(
                query=event.query,
                original_answer=event.answer,
            )
            result["next_action"] = "LIOS will provide more detail next message"

        # Always store the raw event for audit trail
        self.store.append_feedback_event(event)
        result["stored"] = True

        return result

    def get_session_feedback(self, session_id: str) -> list[FeedbackEvent]:
        """Get all feedback events from a session."""
        return self.store.get_session_feedback(session_id)

    def get_corrections_for_topic(self, topic: str) -> list[dict[str, Any]]:
        """Get all corrections related to a topic.
        
        Used for analyzing what LIOS got wrong and how to fix it.
        """
        return self.store.get_corrections_for_topic(topic)

    def summarize_session_learning(self, session_id: str) -> dict[str, Any]:
        """Summarize what LIOS learned from a session.
        
        Returns:
            Dictionary with learning summary including:
            - corrections made
            - instructions given
            - verified answers
            - recommendations for next session
        """
        feedback_events = self.get_session_feedback(session_id)

        summary: dict[str, Any] = {
            "session_id": session_id,
            "total_feedback_events": len(feedback_events),
            "breakdown": {
                "verified": 0,
                "corrections": 0,
                "instructions": 0,
                "partial": 0,
                "saved": 0,
            },
            "corrections": [],
            "instructions": [],
            "verified_answers": [],
        }

        for event in feedback_events:
            summary["breakdown"][event.feedback_type.value] = (
                summary["breakdown"].get(event.feedback_type.value, 0) + 1
            )

            if event.feedback_type == FeedbackType.WRONG:
                summary["corrections"].append(
                    {
                        "was": event.answer,
                        "now": event.feedback_text,
                        "timestamp": event.timestamp,
                    }
                )
            elif event.feedback_type == FeedbackType.INSTRUCT:
                summary["instructions"].append(
                    {
                        "rule": event.feedback_text,
                        "context": event.query,
                        "timestamp": event.timestamp,
                    }
                )
            elif event.feedback_type == FeedbackType.VERIFIED:
                summary["verified_answers"].append(
                    {
                        "query": event.query,
                        "answer": event.answer,
                        "timestamp": event.timestamp,
                    }
                )

        return summary
