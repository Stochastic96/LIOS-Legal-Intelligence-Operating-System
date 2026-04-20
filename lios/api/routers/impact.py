"""Double materiality / impact API routes (/api/impact/*)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from lios.api.dependencies import materiality_engine, require_api_key
from lios.logging_setup import RequestLogger, get_logger
from lios.models.validation import ErrorResponse, MaterialityAssessmentRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/api/impact", dependencies=[Depends(require_api_key)])


@router.post("/materiality")
async def impact_materiality(request: MaterialityAssessmentRequest) -> dict[str, Any]:
    """Run a double materiality assessment (CSRD Art.4 / ESRS 1)."""
    import asyncio

    request_id = str(uuid.uuid4())
    with RequestLogger(logger, "Materiality assessment", request_id=request_id):
        try:
            topic_inputs = [t.model_dump() for t in request.topics]
            matrix = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: materiality_engine.assess(
                    company_profile=request.company_profile,
                    topic_inputs=topic_inputs,
                ),
            )
            return {
                "material_topics": matrix.material_topics,
                "mandatory_topics": matrix.mandatory_topics,
                "recommended_disclosures": matrix.recommended_disclosures,
                "assessment_summary": matrix.assessment_summary,
                "next_steps": matrix.next_steps,
                "csrd_article_references": matrix.csrd_article_references,
                "assessed_topics": [
                    {
                        "esrs_code": t.esrs_code,
                        "topic_name": t.topic_name,
                        "sub_topic": t.sub_topic,
                        "impact_score": t.impact_score,
                        "financial_score": t.financial_score,
                        "double_material": t.double_material,
                        "materiality_level": t.materiality_level,
                        "impact_material": t.impact_material,
                        "financial_material": t.financial_material,
                        "financial_time_horizon": t.financial_time_horizon,
                        "rationale": t.rationale,
                        "priority_actions": t.priority_actions,
                    }
                    for t in matrix.assessed_topics
                ],
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error in materiality assessment (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error running materiality assessment",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@router.get("/esrs-topics")
def impact_esrs_topics() -> dict[str, Any]:
    """Return the full ESRS topic taxonomy for materiality assessment."""
    return {
        "topics": materiality_engine.get_topic_catalog(),
        "reference": "ESRS 1, Appendix A – Full list of sustainability matters",
    }


@router.get("/materiality-template")
def impact_materiality_template(sector: str = "manufacturing") -> dict[str, Any]:
    """Return a pre-populated materiality assessment template for a given sector."""
    inputs = materiality_engine.create_default_assessment_inputs(sector=sector)
    return {
        "sector": sector,
        "topic_inputs": inputs,
        "instructions": (
            "Adjust scores (1–5) based on your company's situation before submitting "
            "to POST /api/impact/materiality. 1=low/unlikely, 5=severe/certain."
        ),
    }
