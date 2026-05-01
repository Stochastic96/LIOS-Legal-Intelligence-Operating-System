"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from lios.agents.unified_agent import UnifiedComplianceAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.orchestration.engine import OrchestrationEngine


@pytest.fixture(scope="session")
def regulatory_db() -> RegulatoryDatabase:
    return RegulatoryDatabase()


@pytest.fixture(scope="session")
def unified_agent(regulatory_db: RegulatoryDatabase) -> UnifiedComplianceAgent:
    return UnifiedComplianceAgent(regulatory_db)


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
def orchestration_engine() -> OrchestrationEngine:
    return OrchestrationEngine()
