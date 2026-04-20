"""Supply chain API routes (/api/supply-chain/*)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from lios.api.dependencies import require_api_key, supply_chain_engine
from lios.logging_setup import RequestLogger, get_logger
from lios.models.validation import ErrorResponse, SupplierRegistrationRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/api/supply-chain", dependencies=[Depends(require_api_key)])


@router.post("/add-supplier")
def supply_chain_add_supplier(request: SupplierRegistrationRequest) -> dict[str, Any]:
    """Register a new supplier with ESG scores."""
    request_id = str(uuid.uuid4())
    with RequestLogger(logger, "Add supplier", request_id=request_id, supplier=request.name):
        try:
            supplier = supply_chain_engine.add_supplier(
                name=request.name,
                country=request.country,
                sector=request.sector,
                tier=request.tier,
                environmental_score=request.environmental_score,
                social_score=request.social_score,
                governance_score=request.governance_score,
                data_quality=request.data_quality,
                annual_spend_eur=request.annual_spend_eur,
                employees=request.employees,
                contact_email=request.contact_email,
                website=request.website,
                certifications=request.certifications,
                notes=request.notes,
            )
            return {
                "supplier_id": supplier.supplier_id,
                "name": supplier.name,
                "country": supplier.country,
                "sector": supplier.sector,
                "tier": supplier.tier,
                "esg_scores": {
                    "environmental": supplier.esg_scores.environmental,
                    "social": supplier.esg_scores.social,
                    "governance": supplier.esg_scores.governance,
                    "composite": supplier.esg_scores.composite,
                    "data_quality": supplier.esg_scores.data_quality,
                },
                "created_at": supplier.created_at,
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error adding supplier (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error registering supplier",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@router.get("/suppliers")
def supply_chain_list_suppliers() -> dict[str, Any]:
    """List all registered suppliers."""
    suppliers = supply_chain_engine.list_suppliers()
    return {
        "total": len(suppliers),
        "suppliers": [
            {
                "supplier_id": s.supplier_id,
                "name": s.name,
                "country": s.country,
                "sector": s.sector,
                "tier": s.tier,
                "composite_esg_score": s.esg_scores.composite,
                "annual_spend_eur": s.annual_spend_eur,
                "audit_status": s.audit_status,
                "certifications": s.certifications,
            }
            for s in suppliers
        ],
    }


@router.get("/risk-assessment")
async def supply_chain_risk_assessment() -> dict[str, Any]:
    """Get risk assessment for all registered suppliers."""
    import asyncio

    request_id = str(uuid.uuid4())
    with RequestLogger(logger, "Supply chain risk assessment", request_id=request_id):
        try:
            assessments, portfolio = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: (
                    supply_chain_engine.assess_all_risks(),
                    supply_chain_engine.get_portfolio_summary(),
                ),
            )
            return {
                "portfolio_summary": {
                    "total_suppliers": portfolio.total_suppliers,
                    "critical_count": portfolio.critical_count,
                    "high_count": portfolio.high_count,
                    "medium_count": portfolio.medium_count,
                    "low_count": portfolio.low_count,
                    "average_esg_score": portfolio.average_esg_score,
                    "total_annual_spend_eur": portfolio.total_annual_spend_eur,
                    "high_risk_spend_eur": portfolio.high_risk_spend_eur,
                    "coverage_percent": portfolio.coverage_percent,
                    "top_risks": portfolio.top_risks,
                    "csrd_compliance_status": portfolio.csrd_compliance_status,
                },
                "supplier_assessments": [
                    {
                        "supplier_id": a.supplier_id,
                        "supplier_name": a.supplier_name,
                        "overall_risk": a.overall_risk,
                        "overall_score": a.overall_score,
                        "csrd_compliance_gaps": a.csrd_compliance_gaps,
                        "recommended_actions": a.recommended_actions,
                        "assessment_date": a.assessment_date,
                        "due_diligence_complete": a.due_diligence_complete,
                        "risk_factors": [
                            {
                                "name": rf.name,
                                "score": rf.score,
                                "weighted_score": rf.weighted_score,
                                "description": rf.description,
                            }
                            for rf in a.risk_factors
                        ],
                    }
                    for a in assessments
                ],
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error in risk assessment (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error generating supply chain risk assessment",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@router.get("/due-diligence-checklist")
def supply_chain_checklist() -> dict[str, Any]:
    """Return the CSRD Art.8 / CSDDD due diligence checklist."""
    return {
        "checklist": supply_chain_engine.get_checklist(),
        "csrd_reference": "CSRD Art.8 – Value chain due diligence",
        "csddd_reference": "CSDDD Art.5, 7, 9, 11",
    }
