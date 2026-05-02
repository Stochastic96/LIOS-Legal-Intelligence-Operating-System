"""Learning system for LIOS dual-mode operation.

Provides:
- Feedback collection and processing (user validates/corrects answers)
- Gap detection (identifies what LIOS doesn't know)
- Training pipeline (stores corrections, updates knowledge base)
- Learning event management (tracks all learning interactions)
"""

from __future__ import annotations

from .feedback_handler import FeedbackEvent, FeedbackHandler
from .gap_detector import GapDetector, GapInfo
from .learning_event_store import LearningEventStore, LearningEvent

__all__ = [
    "FeedbackEvent",
    "FeedbackHandler",
    "GapDetector",
    "GapInfo",
    "LearningEventStore",
    "LearningEvent",
]
