"""FastAPI routes for LIOS."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from lios.config import settings
from lios.features.applicability_checker import ApplicabilityChecker
from lios.features.compliance_roadmap import ComplianceRoadmapGenerator
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.orchestration.engine import OrchestrationEngine

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Legal Intelligence Operating System for EU sustainability compliance.",
)

# Shared instances (initialised once at import time)
_db = RegulatoryDatabase()
_engine = OrchestrationEngine()
_applicability_checker = ApplicabilityChecker()
_roadmap_generator = ComplianceRoadmapGenerator()


# ---- Request / Response models ----

class QueryRequest(BaseModel):
    query: str
    company_profile: dict[str, Any] | None = None
    jurisdictions: list[str] | None = None


class ApplicabilityRequest(BaseModel):
    regulation: str
    company_profile: dict[str, Any]


class RoadmapRequest(BaseModel):
    company_profile: dict[str, Any]


# ---- Endpoints ----

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}


@app.get("/regulations")
def list_regulations() -> list[dict[str, Any]]:
    return _db.get_all_regulations()


@app.get("/regulations/{name}")
def get_regulation(name: str) -> dict[str, Any]:
    reg = _db.get_regulation(name)
    if reg is None:
        raise HTTPException(status_code=404, detail=f"Regulation '{name}' not found.")
    # Exclude module object from response
    return {k: v for k, v in reg.items() if k != "module"}


@app.post("/query")
def query_endpoint(request: QueryRequest) -> dict[str, Any]:
    result = _engine.route_query(
        query=request.query,
        company_profile=request.company_profile,
        jurisdictions=request.jurisdictions,
    )

    return {
        "query": result.query,
        "intent": result.intent,
        "answer": result.answer,
        "consensus_reached": result.consensus_result.consensus_reached,
        "consensus_confidence": result.consensus_result.confidence,
        "citations": [
            {
                "regulation": c.regulation,
                "article_id": c.article_id,
                "title": c.title,
                "relevance_score": c.relevance_score,
                "url": c.url,
            }
            for c in result.citations
        ],
        "decay_scores": [
            {
                "regulation": d.regulation,
                "score": d.score,
                "freshness_label": d.freshness_label,
                "days_since_update": d.days_since_update,
                "last_updated": d.last_updated,
            }
            for d in result.decay_scores
        ],
        "jurisdiction_conflicts": [
            {
                "eu_regulation": c.eu_regulation,
                "national_law": c.national_law,
                "jurisdiction": c.jurisdiction,
                "conflict_type": c.conflict_type,
                "severity": c.severity,
                "description": c.description,
            }
            for c in result.conflicts
        ],
        "roadmap": _serialise_roadmap(result.roadmap),
        "breakdown": _serialise_breakdown(result.breakdown),
        "applicability": _serialise_applicability(result.applicability),
    }


@app.post("/applicability")
def applicability_endpoint(request: ApplicabilityRequest) -> dict[str, Any]:
    result = _applicability_checker.check_applicability(
        request.regulation, request.company_profile
    )
    return {
        "regulation": result.regulation,
        "applicable": result.applicable,
        "reason": result.reason,
        "threshold_details": result.threshold_details,
        "articles_cited": result.articles_cited,
    }


@app.post("/roadmap")
def roadmap_endpoint(request: RoadmapRequest) -> dict[str, Any]:
    roadmap = _roadmap_generator.generate_roadmap(request.company_profile)
    return _serialise_roadmap(roadmap) or {}


# ---- Serialisation helpers ----

def _serialise_roadmap(roadmap: Any) -> dict[str, Any] | None:
    if roadmap is None:
        return None
    return {
        "summary": roadmap.summary,
        "applicable_regulations": roadmap.applicable_regulations,
        "steps": [
            {
                "step_number": s.step_number,
                "title": s.title,
                "description": s.description,
                "deadline": s.deadline,
                "regulation": s.regulation,
                "priority": s.priority,
                "articles_cited": s.articles_cited,
            }
            for s in roadmap.steps
        ],
    }


def _serialise_breakdown(breakdown: Any) -> dict[str, Any] | None:
    if breakdown is None:
        return None
    return {
        "topic": breakdown.topic,
        "regulation": breakdown.regulation,
        "summary": breakdown.summary,
        "key_articles": breakdown.key_articles,
        "obligations": breakdown.obligations,
        "penalties": breakdown.penalties,
        "timeline": breakdown.timeline,
    }


def _serialise_applicability(applicability: Any) -> dict[str, Any] | None:
    if applicability is None:
        return None
    return {
        "regulation": applicability.regulation,
        "applicable": applicability.applicable,
        "reason": applicability.reason,
        "threshold_details": applicability.threshold_details,
        "articles_cited": applicability.articles_cited,
    }
