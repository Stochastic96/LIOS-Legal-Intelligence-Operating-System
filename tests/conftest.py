"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from lios.agents.consensus import ConsensusEngine
from lios.agents.finance_agent import FinanceAgent
from lios.agents.sustainability_agent import SustainabilityAgent
from lios.agents.supply_chain_agent import SupplyChainAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.orchestration.engine import OrchestrationEngine


@pytest.fixture(scope="session")
def regulatory_db() -> RegulatoryDatabase:
    return RegulatoryDatabase()


@pytest.fixture(scope="session")
def sample_company_profile() -> dict:
    return {
        "employees": 600,
        "turnover_eur": 50_000_000,
        "balance_sheet_eur": 25_000_000,
        "listed": False,
        "sector": "manufacturing",
        "jurisdiction": "Germany",
    }


@pytest.fixture(scope="session")
def small_company_profile() -> dict:
    return {
        "employees": 50,
        "turnover_eur": 5_000_000,
        "balance_sheet_eur": 2_000_000,
        "listed": False,
        "sector": "retail",
        "jurisdiction": "Germany",
    }


@pytest.fixture(scope="session")
def finance_company_profile() -> dict:
    return {
        "employees": 800,
        "turnover_eur": 200_000_000,
        "balance_sheet_eur": 1_000_000_000,
        "listed": True,
        "sector": "asset management",
        "jurisdiction": "Germany",
    }


@pytest.fixture(scope="session")
def consensus_engine(regulatory_db: RegulatoryDatabase) -> ConsensusEngine:
    sus = SustainabilityAgent(regulatory_db)
    sc = SupplyChainAgent(regulatory_db)
    fin = FinanceAgent(regulatory_db)
    return ConsensusEngine([sus, sc, fin])


@pytest.fixture(scope="session")
def orchestration_engine() -> OrchestrationEngine:
    return OrchestrationEngine()
