"""Three-agent consensus engine."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from lios.agents.base_agent import AgentResponse, BaseAgent
from lios.config import settings


@dataclass
class ConsensusResult:
    consensus_reached: bool
    answer: str
    citations: list[dict[str, Any]]
    conflict_report: str
    agent_responses: list[AgentResponse]
    confidence: float
    agreeing_agents: list[str] = field(default_factory=list)


class ConsensusEngine:
    """Run N agents in parallel; require ≥ CONSENSUS_THRESHOLD to agree.

    Args:
        agents: Two or more :class:`BaseAgent` instances.
        threshold: Minimum number of agents that must share a keyword to
            declare consensus.  Defaults to ``settings.CONSENSUS_THRESHOLD``.
    """

    def __init__(
        self,
        agents: list[BaseAgent],
        threshold: int | None = None,
    ) -> None:
        if len(agents) < 2:
            raise ValueError("ConsensusEngine requires at least 2 agents.")
        self.agents = agents
        self.threshold = threshold if threshold is not None else settings.CONSENSUS_THRESHOLD

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, query: str, context: dict[str, Any] | None = None) -> ConsensusResult:
        context = context or {}
        responses = self._parallel_analyze(query, context)
        return self._evaluate(responses)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _parallel_analyze(
        self, query: str, context: dict[str, Any]
    ) -> list[AgentResponse]:
        n = len(self.agents)
        results: list[AgentResponse | None] = [None] * n
        errors: list[Exception | None] = [None] * n

        def run_agent(idx: int, agent: BaseAgent) -> None:
            try:
                results[idx] = agent.analyze(query, context)
            except Exception as exc:  # pragma: no cover
                errors[idx] = exc

        threads = [
            threading.Thread(target=run_agent, args=(i, agent))
            for i, agent in enumerate(self.agents)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)  # 30s is generous for rule-based agents; LLM calls may be slower

        # Replace None/errors with fallback responses
        final: list[AgentResponse] = []
        for i, r in enumerate(results):
            if r is None:
                final.append(
                    AgentResponse(
                        agent_name=self.agents[i].name,
                        answer="Agent failed to respond.",
                        citations=[],
                        confidence=0.0,
                        reasoning=str(errors[i]) if errors[i] else "Timeout",
                        conclusion_keywords=["error"],
                    )
                )
            else:
                final.append(r)
        return final

    def _evaluate(self, responses: list[AgentResponse]) -> ConsensusResult:
        """Determine consensus by comparing conclusion keywords."""
        # Build keyword sets per response
        kw_sets = [set(r.conclusion_keywords) for r in responses]

        # Find the largest group that shares at least one common keyword
        best_keyword: str | None = None
        best_count = 0
        best_agents: list[int] = []

        # Collect all unique keywords
        all_keywords: set[str] = set()
        for ks in kw_sets:
            all_keywords.update(ks)

        for kw in all_keywords:
            if kw == "error":
                continue
            agents_with_kw = [i for i, ks in enumerate(kw_sets) if kw in ks]
            if len(agents_with_kw) > best_count:
                best_count = len(agents_with_kw)
                best_keyword = kw
                best_agents = agents_with_kw

        consensus_reached = best_count >= self.threshold

        if consensus_reached:
            # Merge answers from agreeing agents
            agreeing_responses = [responses[i] for i in best_agents]
            combined_answer = self._merge_answers(agreeing_responses)
            combined_citations = self._merge_citations(agreeing_responses)
            avg_confidence = sum(r.confidence for r in agreeing_responses) / len(agreeing_responses)
            conflict_report = ""
            agreeing_agent_names = [r.agent_name for r in agreeing_responses]
        else:
            combined_answer = (
                "⚠️ No consensus reached. The three agents produced conflicting analyses. "
                "Please review individual agent responses below and consult a legal expert."
            )
            combined_citations = self._merge_citations(responses)
            avg_confidence = 0.3
            conflict_report = self._build_conflict_report(responses)
            agreeing_agent_names = []

        return ConsensusResult(
            consensus_reached=consensus_reached,
            answer=combined_answer,
            citations=combined_citations,
            conflict_report=conflict_report,
            agent_responses=responses,
            confidence=avg_confidence,
            agreeing_agents=agreeing_agent_names,
        )

    def _merge_answers(self, responses: list[AgentResponse]) -> str:
        # Primary agent (highest confidence) leads; others add supplementary perspectives
        sorted_responses = sorted(responses, key=lambda r: r.confidence, reverse=True)
        primary = sorted_responses[0]
        others = sorted_responses[1:]

        parts = [
            f"Primary analysis ({primary.agent_name}, confidence {primary.confidence:.0%}):\n"
            f"{primary.answer}"
        ]
        for r in others:
            parts.append(
                f"Additional perspective ({r.agent_name}, confidence {r.confidence:.0%}):\n"
                f"{r.answer}"
            )
        return "\n\n".join(parts)

    def _merge_citations(self, responses: list[AgentResponse]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for r in responses:
            for c in r.citations:
                key = f"{c.get('regulation')}:{c.get('article_id')}"
                if key not in seen:
                    seen.add(key)
                    merged.append(c)
        return merged

    def _build_conflict_report(self, responses: list[AgentResponse]) -> str:
        lines = ["Conflict report – agent conclusions differ:"]
        for r in responses:
            lines.append(
                f"  • {r.agent_name}: keywords={r.conclusion_keywords}, "
                f"confidence={r.confidence:.2f}"
            )
        lines.append(
            "Recommendation: escalate to human legal review given the conflicting analyses."
        )
        return "\n".join(lines)
