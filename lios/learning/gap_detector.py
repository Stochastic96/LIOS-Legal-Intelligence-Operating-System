"""Gap detection system for LIOS Learn Mode.

Identifies what LIOS doesn't know and generates smart questions
to fill knowledge gaps in a structured way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import json


class GapLevel(str, Enum):
    """Completion level of a knowledge node."""

    UNKNOWN = "unknown"  # 0% — LIOS hasn't heard of this
    SEED = "seed"  # 25% — Basic concept known
    LEARNING = "learning"  # 50% — Actively asking about it
    CONNECTED = "connected"  # 75% — Linked to related topics
    FUNCTIONAL = "functional"  # 90% — Can answer basic questions
    MASTERED = "mastered"  # 100% — Expert level


@dataclass
class GapInfo:
    """Information about a knowledge gap."""

    topic: str  # "CSRD", "EU Taxonomy", "Carbon Accounting", etc.
    gap_level: GapLevel
    confidence_score: float  # 0.0-1.0, increases as LIOS learns
    
    related_topics: list[str] = field(default_factory=list)
    suggested_next_topic: Optional[str] = None
    last_asked: Optional[str] = None  # ISO 8601 timestamp
    
    metadata: dict[str, Any] = field(default_factory=dict)

    def merge_suggestion(self, next_topic: str) -> None:
        """Record a suggested next topic."""
        self.suggested_next_topic = next_topic


class GapDetector:
    """Detect knowledge gaps and generate learning questions."""

    def __init__(self, knowledge_map: dict[str, GapInfo]) -> None:
        """Initialize with existing knowledge map.
        
        Args:
            knowledge_map: Dict mapping topic names to GapInfo objects
        """
        self.knowledge_map = knowledge_map

    @classmethod
    def create_default(cls) -> GapDetector:
        """Create detector with default EU sustainability law knowledge map."""
        default_map = {
            # EU Regulatory Framework
            "CSRD": GapInfo(
                topic="CSRD",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                metadata={"category": "EU Regulation", "scope": "reporting"},
            ),
            "EU Taxonomy": GapInfo(
                topic="EU Taxonomy",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                related_topics=["CSRD"],
                metadata={"category": "EU Regulation", "scope": "classification"},
            ),
            "SFDR": GapInfo(
                topic="SFDR",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                related_topics=["EU Taxonomy"],
                metadata={"category": "EU Regulation", "scope": "financial"},
            ),
            "ESRS": GapInfo(
                topic="ESRS",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                related_topics=["CSRD"],
                metadata={"category": "EU Regulation", "scope": "standards"},
            ),
            # Global Frameworks
            "GRI Standards": GapInfo(
                topic="GRI Standards",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                metadata={"category": "Global Framework", "scope": "reporting"},
            ),
            "TCFD": GapInfo(
                topic="TCFD",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                metadata={"category": "Global Framework", "scope": "climate"},
            ),
            "ISSB": GapInfo(
                topic="ISSB",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                related_topics=["TCFD", "CSRD"],
                metadata={"category": "Global Framework", "scope": "standards"},
            ),
            # Core Concepts
            "ESG": GapInfo(
                topic="ESG",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                metadata={"category": "Core Concept", "scope": "definition"},
            ),
            "Materiality": GapInfo(
                topic="Materiality",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                metadata={"category": "Core Concept", "scope": "methodology"},
            ),
            "Greenwashing": GapInfo(
                topic="Greenwashing",
                gap_level=GapLevel.UNKNOWN,
                confidence_score=0.0,
                metadata={"category": "Core Concept", "scope": "risk"},
            ),
        }
        return cls(default_map)

    def get_learning_priorities(self, limit: int = 5) -> list[GapInfo]:
        """Get top learning priorities.
        
        Returns topics that:
        1. LIOS doesn't know yet (gap_level < FUNCTIONAL)
        2. Are foundational (prerequisites for other topics)
        3. Haven't been asked about recently
        
        Args:
            limit: Maximum number of topics to return
            
        Returns:
            Sorted list of GapInfo, highest priority first
        """
        unknowns = [
            gap
            for gap in self.knowledge_map.values()
            if gap.gap_level in (GapLevel.UNKNOWN, GapLevel.SEED)
        ]

        # Prioritize: foundational topics first (those with many dependents)
        def priority_score(gap: GapInfo) -> float:
            # More related topics = higher priority
            related_count = len(gap.related_topics)
            # Recent topics lower priority
            recent_penalty = 0.5 if gap.last_asked else 1.0
            return (1.0 + related_count) * recent_penalty

        unknowns.sort(key=priority_score, reverse=True)
        return unknowns[:limit]

    def detect_gaps_after_query(
        self, query: str, response: str, confidence: float
    ) -> list[str]:
        """Detect gaps revealed by a query/response pair.
        
        Args:
            query: The user's question
            response: LIOS's response
            confidence: LIOS's confidence in the response (0-1)
            
        Returns:
            List of newly detected gap topics
        """
        gaps: list[str] = []

        # If low confidence, mark topics as having gaps
        if confidence < 0.7:
            # Extract potential topic keywords from query
            keywords = query.lower().split()
            for topic_name in self.knowledge_map:
                if any(
                    kw in topic_name.lower() for kw in keywords
                ):
                    gaps.append(topic_name)

        return gaps

    def update_knowledge_level(
        self, topic: str, new_level: GapLevel, confidence: float
    ) -> None:
        """Update knowledge level for a topic.
        
        Args:
            topic: Topic name
            new_level: New GapLevel
            confidence: New confidence score (0-1)
        """
        if topic in self.knowledge_map:
            gap = self.knowledge_map[topic]
            gap.gap_level = new_level
            gap.confidence_score = max(gap.confidence_score, confidence)

    def get_next_question(self) -> tuple[Optional[str], Optional[str]]:
        """Get the next question LIOS should ask the user.
        
        Returns:
            Tuple of (topic_name, question_text) or (None, None) if no gaps
        """
        priorities = self.get_learning_priorities(limit=1)
        if not priorities:
            return None, None

        gap_info = priorities[0]
        topic_name = gap_info.topic

        # Generate appropriate question based on gap level
        questions = {
            GapLevel.UNKNOWN: f"I haven't started learning about {topic_name.lower()}. Can you explain what {topic_name} is?",
            GapLevel.SEED: f"I know {topic_name} exists but I'm hazy on details. What's the key purpose or scope of {topic_name}?",
            GapLevel.LEARNING: f"I'm learning about {topic_name}. Can you tell me about {topic_name} and how it relates to {', '.join(gap_info.related_topics[:2]) or 'sustainability'}?",
            GapLevel.CONNECTED: f"I understand {topic_name} but want to deepen my knowledge. What are the main provisions or concepts in {topic_name}?",
        }

        question = questions.get(gap_info.gap_level, f"Tell me more about {topic_name}?")
        return topic_name, question

    def mark_question_asked(self, topic: str) -> None:
        """Record that LIOS has asked about a topic."""
        if topic in self.knowledge_map:
            from datetime import datetime, timezone
            self.knowledge_map[topic].last_asked = datetime.now(
                timezone.utc
            ).isoformat()
            # Upgrade level to LEARNING
            if self.knowledge_map[topic].gap_level in (
                GapLevel.UNKNOWN,
                GapLevel.SEED,
            ):
                self.knowledge_map[topic].gap_level = GapLevel.LEARNING

    def get_knowledge_map_status(self) -> dict[str, Any]:
        """Get overall knowledge map status.
        
        Returns:
            Dictionary with completion percentages and status.
        """
        total = len(self.knowledge_map)
        by_level = {level: 0 for level in GapLevel}

        for gap in self.knowledge_map.values():
            by_level[gap.gap_level] += 1

        completion_pct = (
            (
                by_level[GapLevel.FUNCTIONAL]
                + by_level[GapLevel.MASTERED]
            )
            * 100
            / total
        )

        return {
            "total_topics": total,
            "by_level": {k.value: v for k, v in by_level.items()},
            "completion_percentage": round(completion_pct, 1),
            "mastered": by_level[GapLevel.MASTERED],
            "functional": by_level[GapLevel.FUNCTIONAL],
            "learning": by_level[GapLevel.LEARNING],
            "not_started": by_level[GapLevel.UNKNOWN] + by_level[GapLevel.SEED],
        }

    def export_knowledge_map(self) -> dict[str, Any]:
        """Export knowledge map as JSON-serializable dict."""
        return {
            topic: {
                "level": gap.gap_level.value,
                "confidence": gap.confidence_score,
                "related": gap.related_topics,
                "last_asked": gap.last_asked,
            }
            for topic, gap in self.knowledge_map.items()
        }
