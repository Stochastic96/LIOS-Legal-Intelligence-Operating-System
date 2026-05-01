"""Tests for the unified compliance agent and base agent logic."""

from __future__ import annotations

import pytest

from lios.agents.base_agent import AgentResponse
from lios.agents.unified_agent import UnifiedComplianceAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase


@pytest.fixture(scope="module")
def db():
    return RegulatoryDatabase()


@pytest.fixture(scope="module")
def agent(db):
    return UnifiedComplianceAgent(db)


def test_agent_returns_response(agent):
    response = agent.analyze("What are CSRD reporting requirements?")
    assert isinstance(response, AgentResponse)
    assert response.agent_name == "unified_compliance_agent"


def test_agent_csrd_thresholds(agent):
    response = agent.analyze("What are CSRD applicability thresholds?")
    assert response.answer
    assert "250" in response.answer or "500" in response.answer or "phase" in response.answer.lower()


def test_agent_double_materiality(agent):
    response = agent.analyze("Does CSRD require double materiality assessment?")
    assert response.answer
    assert "material" in response.answer.lower()


def test_agent_climate_ghg(agent):
    response = agent.analyze("What GHG emissions must be disclosed under ESRS E1?")
    assert "scope" in response.answer.lower() or "ghg" in response.answer.lower() or "climate" in response.answer.lower()


def test_agent_sfdr_classification(agent):
    response = agent.analyze("Difference between SFDR article 8 and article 9 funds")
    assert response.answer
    assert "sfdr" in response.answer.lower() or "article" in response.answer.lower()


def test_agent_supply_chain(agent):
    response = agent.analyze("What are supply chain due diligence requirements under CSRD?")
    assert response.answer
    assert "supply chain" in response.answer.lower() or "value chain" in response.answer.lower()


def test_agent_taxonomy_query(agent):
    response = agent.analyze("What is the EU Taxonomy DNSH criteria?")
    assert response.citations
    assert response.answer


def test_agent_cs3d(agent):
    response = agent.analyze("What are CS3D mandatory due diligence obligations?")
    assert response.answer
    assert "cs3d" in response.answer.lower() or "due diligence" in response.answer.lower()


def test_agent_has_citations(agent):
    response = agent.analyze("CSRD sustainability reporting obligations")
    assert isinstance(response.citations, list)
    for c in response.citations:
        assert "regulation" in c
        assert "article_id" in c


def test_agent_conclusion_keywords(agent):
    response = agent.analyze("Are companies required to report under CSRD?")
    assert isinstance(response.conclusion_keywords, list)
    assert len(response.conclusion_keywords) > 0


def test_agent_confidence_range(agent):
    response = agent.analyze("Supply chain sustainability disclosure")
    assert 0.0 <= response.confidence <= 1.0


def test_agent_has_reasoning(agent):
    response = agent.analyze("SFDR sustainability risk disclosure")
    assert response.reasoning
    assert len(response.reasoning) > 10


def test_agent_handles_empty_query(agent):
    response = agent.analyze("")
    assert isinstance(response, AgentResponse)
    assert response.answer


def test_agent_covers_all_regulations(agent):
    assert "CSRD" in agent.primary_regulations
    assert "ESRS" in agent.primary_regulations
    assert "EU_TAXONOMY" in agent.primary_regulations
    assert "SFDR" in agent.primary_regulations
    assert "CS3D" in agent.primary_regulations


def test_agent_answer_has_legal_structure(agent):
    response = agent.analyze("What are CSRD reporting requirements?")
    # Answer should contain retrieved legal provisions or analysis
    assert "##" in response.answer or len(response.answer) > 100
