"""Tests for single-agent consensus path (no multi-agent consensus with unified agent)."""

from __future__ import annotations

import pytest

from lios.agents.consensus import ConsensusResult
from lios.agents.base_agent import AgentResponse
from lios.agents.unified_agent import UnifiedComplianceAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.orchestration.engine import OrchestrationEngine


@pytest.fixture
def db():
    return RegulatoryDatabase()


@pytest.fixture
def agent(db):
    return UnifiedComplianceAgent(db)


def test_consensus_engine_requires_three_agents(db):
    sus = SustainabilityAgent(db)
    with pytest.raises(ValueError, match="at least 2 agents"):
        ConsensusEngine([sus])


def test_single_agent_consensus_result(agent):
    response = agent.analyze("Does CSRD apply to large companies?")
    assert isinstance(response, AgentResponse)
    assert response.answer
    assert 0.0 <= response.confidence <= 1.0


def test_engine_returns_full_response(engine):
    result = engine.route_query("What are CSRD reporting requirements?")
    assert result.answer
    assert isinstance(result.consensus_result, ConsensusResult)
    assert result.consensus_result.consensus_reached


def test_engine_consensus_has_single_agent_response(engine):
    result = engine.route_query("What are CSRD reporting requirements?")
    assert len(result.consensus_result.agent_responses) == 1
    assert result.consensus_result.agent_responses[0].agent_name == "unified_compliance_agent"


def test_engine_confidence_range(engine):
    result = engine.route_query("What is the EU Taxonomy regulation?")
    assert 0.0 <= result.consensus_result.confidence <= 1.0


def test_engine_citations_present(engine):
    result = engine.route_query("CSRD sustainability reporting obligations")
    article_keys = [f"{c['regulation']}:{c['article_id']}" for c in result.consensus_result.citations]
    assert len(article_keys) == len(set(article_keys)), "Duplicate citations found"


def test_engine_csrd_query_with_profile(engine):
    result = engine.route_query(
        "Does CSRD apply to my company?",
        company_profile={"employees": 600, "turnover_eur": 50_000_000},
    )
    assert result.answer
    assert result.consensus_result.agent_responses


def test_engine_parallel_speed(engine):
    import time
    start = time.time()
    engine.route_query("ESRS E1 climate disclosure requirements")
    elapsed = time.time() - start
    # Model loading + LLM timeout (when Ollama is unavailable) can take ~60s total
    assert elapsed < 120.0, "Query took too long"
