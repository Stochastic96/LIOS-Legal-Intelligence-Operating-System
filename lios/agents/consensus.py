"""
Three-agent consensus engine.

Three specialist agents respond independently to the same query.
Consensus is computed via answer similarity; if agents disagree,
the conflict is flagged rather than a single answer being guessed.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

from lios.agents.base_agent import AgentResponse
from lios.config import settings
from lios.utils.logger import get_logger

logger = get_logger(__name__)


def _similarity(a: str, b: str) -> float:
    """Normalised string similarity in [0, 1]."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


@dataclass
class ConsensusResult:
    consensus_reached: bool
    consensus_score: float         # 0.0 – 1.0 (average pairwise answer similarity)
    merged_answer: Optional[str]   # None if consensus not reached
    conflict_summary: Optional[str]
    agent_responses: list[AgentResponse] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)


class ConsensusEngine:
    """
    Aggregates responses from three agents and determines consensus.

    Consensus is reached when the average pairwise answer similarity
    exceeds ``settings.consensus_threshold``.
    """

    def __init__(self, threshold: Optional[float] = None) -> None:
        self.threshold = threshold or settings.consensus_threshold

    def evaluate(self, responses: list[AgentResponse]) -> ConsensusResult:
        if not responses:
            return ConsensusResult(
                consensus_reached=False,
                consensus_score=0.0,
                merged_answer=None,
                conflict_summary="No agent responses received.",
            )

        answers = [r.answer for r in responses]

        # Pairwise similarity
        pairs = [
            _similarity(answers[i], answers[j])
            for i in range(len(answers))
            for j in range(i + 1, len(answers))
        ]
        score = statistics.mean(pairs) if pairs else 1.0

        # Merge citations from all agents (deduplicated by regulation+article)
        seen: set[str] = set()
        merged_citations: list[dict] = []
        for r in responses:
            for c in r.citations:
                key = f"{c.get('regulation')}:{c.get('article')}"
                if key not in seen:
                    seen.add(key)
                    merged_citations.append(c)

        if score >= self.threshold:
            # Pick the answer with the highest confidence
            best = max(responses, key=lambda r: r.confidence)
            return ConsensusResult(
                consensus_reached=True,
                consensus_score=round(score, 4),
                merged_answer=best.answer,
                conflict_summary=None,
                agent_responses=responses,
                citations=merged_citations,
            )

        # Consensus not reached – summarise disagreement
        conflict_summary = self._summarise_conflict(responses, score)
        logger.warning(
            "Consensus NOT reached (score=%.2f < threshold=%.2f). Flagging conflict.",
            score,
            self.threshold,
        )
        return ConsensusResult(
            consensus_reached=False,
            consensus_score=round(score, 4),
            merged_answer=None,
            conflict_summary=conflict_summary,
            agent_responses=responses,
            citations=merged_citations,
        )

    @staticmethod
    def _summarise_conflict(responses: list[AgentResponse], score: float) -> str:
        lines = [
            f"⚠ Agent consensus score: {score:.0%} (below threshold). "
            "The agents provided diverging answers. Manual review is required.\n"
        ]
        for r in responses:
            lines.append(f"• [{r.agent_id}] (confidence={r.confidence:.0%}): {r.answer[:300]}")
        return "\n".join(lines)
