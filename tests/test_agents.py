"""Tests for all three domain agents and base agent logic."""

from __future__ import annotations

import pytest

from lios.agents.base_agent import AgentResponse
from lios.agents.finance_agent import FinanceAgent
from lios.agents.sustainability_agent import SustainabilityAgent
from lios.agents.supply_chain_agent import SupplyChainAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase


@pytest.fixture(scope="module")
def db():
    return RegulatoryDatabase()


@pytest.fixture(scope="module")
def sustainability_agent(db):
    return SustainabilityAgent(db)


@pytest.fixture(scope="module")
def supply_chain_agent(db):
    return SupplyChainAgent(db)


@pytest.fixture(scope="module")
def finance_agent(db):
    return FinanceAgent(db)


# ---- Sustainability Agent ----

def test_sustainability_agent_returns_response(sustainability_agent):
    response = sustainability_agent.analyze("What are CSRD reporting requirements?")
    assert isinstance(response, AgentResponse)
    assert response.agent_name == "sustainability_agent"


def test_sustainability_agent_csrd_query(sustainability_agent):
    response = sustainability_agent.analyze("Does CSRD require double materiality assessment?")
    assert response.answer
    assert response.confidence > 0


def test_sustainability_agent_climate_query(sustainability_agent):
    response = sustainability_agent.analyze(
        "What GHG emissions must be disclosed under ESRS E1?"
    )
    assert "scope" in response.answer.lower() or "ghg" in response.answer.lower() or "climate" in response.answer.lower()


def test_sustainability_agent_taxonomy_query(sustainability_agent):
    response = sustainability_agent.analyze("What is the EU Taxonomy DNSH criteria?")
    assert response.citations


def test_sustainability_agent_has_citations(sustainability_agent):
    response = sustainability_agent.analyze("CSRD sustainability reporting obligations")
    assert isinstance(response.citations, list)
    for c in response.citations:
        assert "regulation" in c
        assert "article_id" in c


def test_sustainability_agent_conclusion_keywords(sustainability_agent):
    response = sustainability_agent.analyze("Are companies required to report under CSRD?")
    assert isinstance(response.conclusion_keywords, list)
    assert len(response.conclusion_keywords) > 0


# ---- Supply Chain Agent ----

def test_supply_chain_agent_returns_response(supply_chain_agent):
    response = supply_chain_agent.analyze("What are supply chain due diligence requirements?")
    assert isinstance(response, AgentResponse)
    assert response.agent_name == "supply_chain_agent"


def test_supply_chain_agent_supplier_query(supply_chain_agent):
    response = supply_chain_agent.analyze("Must we report on our suppliers?")
    assert response.answer


def test_supply_chain_agent_worker_query(supply_chain_agent):
    response = supply_chain_agent.analyze("What are ESRS S2 requirements for value chain workers?")
    assert response.answer


def test_supply_chain_agent_confidence_range(supply_chain_agent):
    response = supply_chain_agent.analyze("Supply chain sustainability disclosure")
    assert 0.0 <= response.confidence <= 1.0


# ---- Finance Agent ----

def test_finance_agent_returns_response(finance_agent):
    response = finance_agent.analyze("What is SFDR article 8 classification?")
    assert isinstance(response, AgentResponse)
    assert response.agent_name == "finance_agent"


def test_finance_agent_sfdr_query(finance_agent):
    response = finance_agent.analyze("Difference between SFDR article 8 and article 9 funds")
    assert response.answer
    # Should mention SFDR or classification
    assert "sfdr" in response.answer.lower() or "article" in response.answer.lower()


def test_finance_agent_pai_query(finance_agent):
    response = finance_agent.analyze("What are principal adverse impact indicators under SFDR?")
    assert response.answer


def test_finance_agent_taxonomy_alignment(finance_agent):
    response = finance_agent.analyze("How to disclose EU taxonomy alignment for financial products?")
    assert response.answer
    assert response.citations


def test_finance_agent_has_reasoning(finance_agent):
    response = finance_agent.analyze("SFDR sustainability risk disclosure")
    assert response.reasoning
    assert len(response.reasoning) > 10


# ---- Cross-agent tests ----

def test_all_agents_have_different_names(db):
    agents = [SustainabilityAgent(db), SupplyChainAgent(db), FinanceAgent(db)]
    names = [a.name for a in agents]
    assert len(names) == len(set(names)), "Agent names must be unique"


def test_all_agents_have_different_domains(db):
    agents = [SustainabilityAgent(db), SupplyChainAgent(db), FinanceAgent(db)]
    domains = [a.domain for a in agents]
    assert len(domains) == len(set(domains)), "Agent domains must be unique"


def test_agents_handle_empty_query_gracefully(db):
    for AgentClass in [SustainabilityAgent, SupplyChainAgent, FinanceAgent]:
        agent = AgentClass(db)
        response = agent.analyze("")
        assert isinstance(response, AgentResponse)
        assert response.answer  # Should return something even for empty query
