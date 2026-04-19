"""Shared FastAPI dependencies and singleton service instances."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Header, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from lios.config import settings
from lios.features.applicability_checker import ApplicabilityChecker
from lios.features.carbon_accounting import CarbonAccountingEngine
from lios.features.chat_training import LocalTrainingStore
from lios.features.compliance_roadmap import ComplianceRoadmapGenerator
from lios.features.materiality import DoubleMaterialityEngine
from lios.features.supply_chain import SupplyChainDueDiligenceEngine
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.orchestration.engine import OrchestrationEngine

# ---------------------------------------------------------------------------
# Shared service singletons – initialised once at import time.
# ---------------------------------------------------------------------------

db = RegulatoryDatabase()
engine = OrchestrationEngine()
applicability_checker = ApplicabilityChecker()
roadmap_generator = ComplianceRoadmapGenerator()
training_store = LocalTrainingStore()
carbon_engine = CarbonAccountingEngine()
supply_chain_engine = SupplyChainDueDiligenceEngine()
materiality_engine = DoubleMaterialityEngine()

# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(x_api_key: str | None = Security(_api_key_header)) -> str | None:
    """FastAPI dependency that enforces API key when configured.

    * If ``LIOS_API_KEY`` is not set (or empty), all requests are allowed.
    * If ``LIOS_API_KEY`` is set, the ``X-API-Key`` header must match.
    """
    if not settings.API_KEY_REQUIRED:
        return x_api_key

    if not x_api_key or x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Provide a valid X-API-Key header.",
        )
    return x_api_key
