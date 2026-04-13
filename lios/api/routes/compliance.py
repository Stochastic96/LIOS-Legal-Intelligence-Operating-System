"""Compliance query endpoints – the primary LIOS API surface."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from lios.agents.features.applicability_checker import (
    ApplicabilityChecker,
    CompanyProfile,
    RegulationType,
)
from lios.agents.features.conflict_mapper import ConflictMapper
from lios.agents.features.legal_breakdown import LegalBreakdownEngine
from lios.agents.features.roadmap_generator import RoadmapGenerator
from lios.agents.orchestrator import Orchestrator

router = APIRouter(prefix="/compliance", tags=["compliance"])

# Shared singletons (stateless, safe to reuse)
_orchestrator = Orchestrator()
_checker = ApplicabilityChecker()
_roadmap = RoadmapGenerator()
_conflicts = ConflictMapper()
_breakdown = LegalBreakdownEngine()


# ── Request / Response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2_000, description="Legal question")
    jurisdiction: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code")
    top_k: int = Field(5, ge=1, le=20, description="Number of KB chunks to retrieve")


class QueryResponse(BaseModel):
    query_id: str
    query: str
    answer: Optional[str]
    consensus_reached: bool
    consensus_score: float
    decay_score: Optional[float]
    decay_label: Optional[str]
    decay_warning: Optional[str]
    conflict_summary: Optional[str]
    jurisdiction_conflicts: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    agent_responses: dict[str, str]


class ApplicabilityRequest(BaseModel):
    name: str
    employees: int = Field(..., ge=0)
    turnover_eur: float = Field(..., ge=0)
    balance_sheet_eur: float = Field(..., ge=0)
    is_listed: bool = False
    is_financial_sector: bool = False
    jurisdiction: str = "EU"
    sector: Optional[str] = None
    regulation: Optional[str] = Field(
        None,
        description="Check a specific regulation (e.g. 'CSRD'). Leave empty to check all."
    )


class RoadmapRequest(BaseModel):
    name: str
    employees: int = Field(..., ge=0)
    turnover_eur: float = Field(..., ge=0)
    balance_sheet_eur: float = Field(..., ge=0)
    is_listed: bool = False
    is_financial_sector: bool = False
    jurisdiction: str = "EU"
    sector: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query_compliance(req: QueryRequest) -> QueryResponse:
    """
    Submit a legal question and receive a consensus-grounded answer.

    The response includes:
    - merged answer (or conflict summary if agents disagree)
    - decay score (regulation freshness)
    - jurisdiction conflict flags
    - article-level citations
    """
    result = await _orchestrator.handle(
        query=req.query,
        jurisdiction=req.jurisdiction,
        top_k=req.top_k,
    )
    return QueryResponse(**result.__dict__)


@router.post("/applicability")
async def check_applicability(req: ApplicabilityRequest) -> dict[str, Any]:
    """
    Check whether one or more EU sustainability regulations apply to a company.
    """
    profile = CompanyProfile(
        name=req.name,
        employees=req.employees,
        turnover_eur=req.turnover_eur,
        balance_sheet_eur=req.balance_sheet_eur,
        is_listed=req.is_listed,
        is_financial_sector=req.is_financial_sector,
        jurisdiction=req.jurisdiction,
        sector=req.sector,
    )

    if req.regulation:
        try:
            reg_type = RegulationType(req.regulation.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown regulation '{req.regulation}'. "
                       f"Valid values: {[r.value for r in RegulationType]}",
            )
        result = _checker.check(profile, reg_type)
        return result.__dict__

    results = _checker.check_all(profile)
    return {
        "company": req.name,
        "results": [r.__dict__ for r in results],
    }


@router.post("/roadmap")
async def generate_roadmap(req: RoadmapRequest) -> dict[str, Any]:
    """
    Generate a personalised compliance roadmap for a company.
    """
    profile = CompanyProfile(
        name=req.name,
        employees=req.employees,
        turnover_eur=req.turnover_eur,
        balance_sheet_eur=req.balance_sheet_eur,
        is_listed=req.is_listed,
        is_financial_sector=req.is_financial_sector,
        jurisdiction=req.jurisdiction,
        sector=req.sector,
    )
    roadmap = _roadmap.generate(profile)
    return roadmap.to_dict()


@router.get("/conflicts")
async def list_conflicts(
    query: str,
    jurisdiction: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return a cross-jurisdiction conflict map for a given query.
    """
    mapper = ConflictMapper(jurisdictions=[jurisdiction] if jurisdiction else None)
    conflict_map = mapper.map(query)
    return conflict_map.to_dict()


@router.get("/breakdown/{regulation}")
async def get_breakdown(regulation: str) -> dict[str, Any]:
    """
    Return a structured section-by-section breakdown of a regulation.
    """
    bd = _breakdown.get(regulation)
    if bd is None:
        available = _breakdown.list_available()
        raise HTTPException(
            status_code=404,
            detail=f"No breakdown available for '{regulation}'. Available: {available}",
        )
    return bd.to_dict()
