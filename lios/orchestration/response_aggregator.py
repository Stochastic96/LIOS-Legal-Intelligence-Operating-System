"""Response aggregator – merges agent responses into a unified view."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lios.agents.base_agent import AgentResponse


@dataclass
class AggregatedResponse:
    answer: str
    citations: list[dict[str, Any]]
    consensus_score: float  # 0.0 – 1.0
    agent_count: int
    agreeing_agents: list[str]
    diverging_agents: list[str]


class ResponseAggregator:
    """Merge a list of AgentResponses into a single AggregatedResponse."""

    def aggregate(self, agent_responses: list[AgentResponse]) -> AggregatedResponse:
        if not agent_responses:
            return AggregatedResponse(
                answer="No agent responses to aggregate.",
                citations=[],
                consensus_score=0.0,
                agent_count=0,
                agreeing_agents=[],
                diverging_agents=[],
            )

        citations = self._merge_citations(agent_responses)
        consensus_score, agreeing, diverging = self._score_consensus(agent_responses)
        answer = self._build_answer(agent_responses, agreeing)

        return AggregatedResponse(
            answer=answer,
            citations=citations,
            consensus_score=consensus_score,
            agent_count=len(agent_responses),
            agreeing_agents=agreeing,
            diverging_agents=diverging,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _merge_citations(self, responses: list[AgentResponse]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        # Sort by confidence desc to prefer high-confidence citations first
        sorted_responses = sorted(responses, key=lambda r: r.confidence, reverse=True)
        for r in sorted_responses:
            for c in r.citations:
                key = f"{c.get('regulation')}:{c.get('article_id')}"
                if key not in seen:
                    seen.add(key)
                    merged.append(c)
        return merged

    def _score_consensus(
        self, responses: list[AgentResponse]
    ) -> tuple[float, list[str], list[str]]:
        """Score consensus and identify agreeing/diverging agents."""
        if len(responses) == 1:
            return 1.0, [responses[0].agent_name], []

        # Build keyword → agent mapping
        kw_to_agents: dict[str, list[str]] = {}
        for r in responses:
            for kw in r.conclusion_keywords:
                kw_to_agents.setdefault(kw, []).append(r.agent_name)

        # Find the keyword shared by the most agents
        best_agents: list[str] = []
        for agents in kw_to_agents.values():
            if len(agents) > len(best_agents):
                best_agents = agents

        all_agents = [r.agent_name for r in responses]
        diverging = [a for a in all_agents if a not in best_agents]
        score = len(best_agents) / len(responses)
        return score, list(set(best_agents)), diverging

    def _build_answer(
        self, responses: list[AgentResponse], agreeing: list[str]
    ) -> str:
        primary = [r for r in responses if r.agent_name in agreeing]
        if not primary:
            primary = responses
        parts = [f"[{r.agent_name}]: {r.answer}" for r in primary]
        return "\n\n---\n\n".join(parts)
