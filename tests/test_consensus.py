"""Tests for consensus engine."""

from __future__ import annotations

import pytest

from lios.agents.consensus import ConsensusEngine, ConsensusResult
from lios.agents.base_agent import AgentResponse
from lios.agents.sustainability_agent import SustainabilityAgent
from lios.agents.supply_chain_agent import SupplyChainAgent
from lios.agents.finance_agent import FinanceAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase


@pytest.fixture
def db():
    return RegulatoryDatabase()


@pytest.fixture
def engine(db):
    sus = SustainabilityAgent(db)
    sc = SupplyChainAgent(db)
    fin = FinanceAgent(db)
    return ConsensusEngine([sus, sc, fin])


def test_consensus_engine_requires_three_agents(db):
    sus = SustainabilityAgent(db)
    with pytest.raises(ValueError, match="exactly 3 agents"):
        ConsensusEngine([sus, sus])


def test_consensus_run_returns_result(engine):
    result = engine.run("Does CSRD apply to large companies?")
    assert isinstance(result, ConsensusResult)
    assert result.answer
    assert isinstance(result.consensus_reached, bool)
    assert 0.0 <= result.confidence <= 1.0


def test_consensus_result_has_three_responses(engine):
    result = engine.run("What are CSRD reporting requirements?")
    assert len(result.agent_responses) == 3
    agent_names = [r.agent_name for r in result.agent_responses]
    assert "sustainability_agent" in agent_names
    assert "supply_chain_agent" in agent_names
    assert "finance_agent" in agent_names


def test_consensus_citations_merged(engine):
    result = engine.run("CSRD sustainability reporting obligations")
    # Citations should be deduplicated across agents
    article_keys = [f"{c['regulation']}:{c['article_id']}" for c in result.citations]
    assert len(article_keys) == len(set(article_keys)), "Duplicate citations found"


def test_consensus_on_csrd_query(engine):
    result = engine.run(
        "Does CSRD apply to companies with more than 500 employees?",
        context={"company_profile": {"employees": 600}},
    )
    assert result.answer
    # At least some response should be non-empty
    assert any(r.answer for r in result.agent_responses)


def test_consensus_confidence_range(engine):
    result = engine.run("What is the EU Taxonomy regulation?")
    assert 0.0 <= result.confidence <= 1.0


def test_consensus_agreeing_agents_subset(engine):
    result = engine.run("SFDR article 8 ESG fund disclosure requirements")
    if result.consensus_reached:
        # Agreeing agents should be a subset of all agents
        all_names = {r.agent_name for r in result.agent_responses}
        for name in result.agreeing_agents:
            assert name in all_names


def test_consensus_conflict_report_when_no_consensus():
    """Force a scenario where agents disagree by using dummy responses."""
    from lios.agents.consensus import ConsensusEngine
    from unittest.mock import MagicMock, patch

    db = RegulatoryDatabase()
    sus = SustainabilityAgent(db)
    sc = SupplyChainAgent(db)
    fin = FinanceAgent(db)
    engine = ConsensusEngine([sus, sc, fin])

    # Patch agent responses to return mutually exclusive keywords
    responses = [
        AgentResponse("a1", "answer1", [], 0.8, "reasoning1", conclusion_keywords=["applies"]),
        AgentResponse("a2", "answer2", [], 0.8, "reasoning2", conclusion_keywords=["exemption_possible"]),
        AgentResponse("a3", "answer3", [], 0.8, "reasoning3", conclusion_keywords=["out_of_scope"]),
    ]

    result = engine._evaluate(responses)
    # With all unique keywords, best_count=1 < threshold=2 → no consensus
    assert not result.consensus_reached
    assert result.conflict_report


def test_consensus_parallel_execution_speed(engine):
    """Ensure parallel execution completes in reasonable time."""
    import time
    start = time.time()
    engine.run("ESRS E1 climate disclosure requirements")
    elapsed = time.time() - start
    assert elapsed < 10.0, "Parallel execution took too long"
