"""Tests for the three-agent consensus engine."""

from __future__ import annotations

import pytest

from lios.agents.base_agent import AgentResponse
from lios.agents.consensus import ConsensusEngine


@pytest.fixture
def engine():
    return ConsensusEngine(threshold=0.3)


def _make_response(agent_id: str, answer: str, confidence: float = 0.9) -> AgentResponse:
    return AgentResponse(
        agent_id=agent_id,
        answer=answer,
        citations=[{"regulation": "CSRD", "article": "Art. 3", "excerpt": "…"}],
        confidence=confidence,
    )


class TestConsensusEngine:
    def test_consensus_reached_on_similar_answers(self, engine: ConsensusEngine) -> None:
        responses = [
            _make_response("sustainability", "CSRD applies to large companies with more than 250 employees."),
            _make_response("supply_chain",   "CSRD applies to large companies with more than 250 employees."),
            _make_response("finance",        "CSRD covers large companies exceeding 250 employees."),
        ]
        result = engine.evaluate(responses)
        assert result.consensus_reached is True
        assert result.consensus_score > 0.3
        assert result.merged_answer is not None

    def test_consensus_not_reached_on_diverging_answers(self) -> None:
        strict_engine = ConsensusEngine(threshold=0.99)
        responses = [
            _make_response("sustainability", "CSRD applies to all companies in the EU regardless of size."),
            _make_response("supply_chain",   "SFDR only applies to financial market participants."),
            _make_response("finance",        "The EU Taxonomy covers economic activities, not companies directly."),
        ]
        result = strict_engine.evaluate(responses)
        assert result.consensus_reached is False
        assert result.merged_answer is None
        assert result.conflict_summary is not None

    def test_empty_responses_returns_no_consensus(self, engine: ConsensusEngine) -> None:
        result = engine.evaluate([])
        assert result.consensus_reached is False
        assert result.consensus_score == 0.0

    def test_citations_merged_across_agents(self, engine: ConsensusEngine) -> None:
        r1 = _make_response("a", "CSRD applies.")
        r1.citations = [{"regulation": "CSRD", "article": "Art. 3", "excerpt": "…"}]
        r2 = _make_response("b", "CSRD applies to large companies.")
        r2.citations = [{"regulation": "CSRD", "article": "Art. 19a", "excerpt": "…"}]

        result = engine.evaluate([r1, r2])
        articles = {c["article"] for c in result.citations}
        assert "Art. 3" in articles
        assert "Art. 19a" in articles

    def test_best_confidence_selected_for_merged_answer(self, engine: ConsensusEngine) -> None:
        responses = [
            _make_response("a", "CSRD applies to large companies.", confidence=0.6),
            _make_response("b", "CSRD applies to large companies.", confidence=0.95),
            _make_response("c", "CSRD applies to large companies.", confidence=0.7),
        ]
        result = engine.evaluate(responses)
        assert result.consensus_reached is True
        assert result.merged_answer == "CSRD applies to large companies."
