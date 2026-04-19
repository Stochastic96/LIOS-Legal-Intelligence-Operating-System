"""Core API routes: health, regulations, query, applicability, roadmap, admin."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from lios.api.dependencies import (
    applicability_checker,
    db,
    engine,
    require_api_key,
    roadmap_generator,
)
from lios.config import settings
from lios.logging_setup import RequestLogger, get_logger
from lios.models.validation import (
    ApplicabilityRequest,
    ErrorResponse,
    FullQueryResponse,
    HealthResponse,
    QueryRequest,
    RoadmapRequest,
)
from datetime import datetime, timezone

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(require_api_key)])


# ---------------------------------------------------------------------------
# Health & metadata
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, dependencies=[])  # no auth on health
def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components={
            "database": "ok",
            "engine": "ok",
        },
    )


@router.get("/regulations")
def list_regulations() -> list[dict[str, Any]]:
    """List all available regulations."""
    logger.debug("Listing all regulations")
    return db.get_all_regulations()


@router.get("/regulations/{name}")
def get_regulation(name: str) -> dict[str, Any]:
    """Get a specific regulation by name."""
    logger.debug(f"Fetching regulation: {name}")
    reg = db.get_regulation(name)
    if reg is None:
        request_id = str(uuid.uuid4())
        logger.warning(f"Regulation not found: {name} (request_id={request_id})")
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=f"Regulation '{name}' not found",
                error_type="not_found",
                request_id=request_id,
            ).model_dump(),
        )
    return {k: v for k, v in reg.items() if k != "module"}


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

@router.post("/query", response_model=FullQueryResponse)
async def query_endpoint(request: QueryRequest) -> FullQueryResponse:
    """Process a legal compliance query."""
    import asyncio

    request_id = str(uuid.uuid4())

    with RequestLogger(logger, "Query processing", request_id=request_id, query=request.query[:100]):
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: engine.route_query(
                    query=request.query,
                    company_profile=request.company_profile.model_dump() if request.company_profile else None,
                    jurisdictions=request.jurisdictions,
                ),
            )

            return FullQueryResponse(
                query=result.query,
                intent=result.intent,
                answer=result.answer,
                citations=[
                    {
                        "regulation": c.regulation,
                        "article_id": c.article_id,
                        "title": c.title,
                        "relevance_score": c.relevance_score,
                        "url": c.url,
                    }
                    for c in result.citations
                ],
                decay_scores=[
                    {
                        "regulation": d.regulation,
                        "score": d.score,
                        "freshness_label": d.freshness_label,
                        "days_since_update": d.days_since_update,
                        "last_updated": d.last_updated,
                    }
                    for d in result.decay_scores
                ],
                conflicts=[
                    {
                        "regulation": c.eu_regulation,
                        "jurisdiction_1": c.eu_regulation,
                        "jurisdiction_2": c.jurisdiction,
                        "conflict_type": c.conflict_type,
                        "description": c.description,
                        "severity": c.severity,
                    }
                    for c in result.conflicts
                ],
                consensus={
                    "reached": result.consensus_result.consensus_reached,
                    "confidence": result.consensus_result.confidence,
                    "agreeing_agents": result.consensus_result.agreeing_agents,
                    "diverging_agents": [
                        a.agent_name for a in result.consensus_result.agent_responses
                        if a.agent_name not in result.consensus_result.agreeing_agents
                    ],
                    "total_agents": len(result.consensus_result.agent_responses),
                },
                roadmap=_serialise_roadmap(result.roadmap),
                breakdown=_serialise_breakdown(result.breakdown),
                applicability=_serialise_applicability(result.applicability),
                metadata={"request_id": request_id},
            )
        except Exception as e:
            logger.error(f"Error processing query (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Internal server error while processing query",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


# ---------------------------------------------------------------------------
# Applicability
# ---------------------------------------------------------------------------

@router.post("/applicability")
async def applicability_endpoint(request: ApplicabilityRequest) -> dict[str, Any]:
    """Check if a regulation applies to a company."""
    import asyncio

    request_id = str(uuid.uuid4())

    with RequestLogger(logger, "Applicability check", request_id=request_id, regulation=request.regulation):
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: applicability_checker.check_applicability(
                    request.regulation,
                    request.company_profile.model_dump(),
                ),
            )
            return {
                "regulation": result.regulation,
                "applicable": result.applicable,
                "reason": result.reason,
                "threshold_details": result.threshold_details,
                "articles_cited": result.articles_cited,
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error checking applicability (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error checking regulation applicability",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------

@router.post("/roadmap")
async def roadmap_endpoint(request: RoadmapRequest) -> dict[str, Any]:
    """Generate a compliance roadmap."""
    import asyncio

    request_id = str(uuid.uuid4())

    with RequestLogger(logger, "Roadmap generation", request_id=request_id):
        try:
            roadmap = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: roadmap_generator.generate_roadmap(request.company_profile.model_dump()),
            )
            return {
                **(_serialise_roadmap(roadmap) or {}),
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error generating roadmap (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error generating compliance roadmap",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


# ---------------------------------------------------------------------------
# Admin – regulatory data refresh
# ---------------------------------------------------------------------------

@router.post("/admin/regulations/refresh")
def admin_refresh_regulations() -> dict[str, Any]:
    """Reload the in-memory regulatory database from source modules.

    Useful after updating regulation data files without restarting the server.
    Protected by the same API key as all other authenticated endpoints.
    """
    try:
        db._load_all()
        logger.info("Regulatory database reloaded by admin request.")
        return {
            "status": "ok",
            "regulations_loaded": len(db.get_all_regulations()),
            "message": "Regulatory database reloaded successfully.",
        }
    except Exception as e:
        logger.error(f"Admin reload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Failed to reload regulatory database",
                error_type="internal",
            ).model_dump(),
        )



# ---------------------------------------------------------------------------
# Serialisation helpers (shared across routers)
# ---------------------------------------------------------------------------

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
