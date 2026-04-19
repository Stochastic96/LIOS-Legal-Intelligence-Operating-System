"""Carbon accounting API routes (/api/carbon/*)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from lios.api.dependencies import carbon_engine, require_api_key
from lios.features.carbon_accounting import Scope1Input, Scope2Input, Scope3Input
from lios.logging_setup import RequestLogger, get_logger
from lios.models.validation import CarbonCalculationRequest, ErrorResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/carbon", dependencies=[Depends(require_api_key)])


@router.post("/calculate")
async def carbon_calculate(request: CarbonCalculationRequest) -> dict[str, Any]:
    """Calculate GHG emissions (Scope 1, 2, 3) – GHG Protocol / CSRD ESRS E1 aligned."""
    import asyncio

    request_id = str(uuid.uuid4())
    with RequestLogger(logger, "Carbon calculation", request_id=request_id):
        try:
            s1 = Scope1Input(
                natural_gas_mwh=request.scope1.natural_gas_mwh,
                diesel_litres=request.scope1.diesel_litres,
                petrol_litres=request.scope1.petrol_litres,
                coal_tonnes=request.scope1.coal_tonnes,
                fuel_oil_litres=request.scope1.fuel_oil_litres,
                lpg_litres=request.scope1.lpg_litres,
                process_emissions_tco2e=request.scope1.process_emissions_tco2e,
                notes=request.scope1.notes,
            )
            s2 = Scope2Input(
                electricity_mwh=request.scope2.electricity_mwh,
                district_heat_mwh=request.scope2.district_heat_mwh,
                steam_mwh=request.scope2.steam_mwh,
                country=request.scope2.country,
                use_market_based=request.scope2.use_market_based,
                market_based_factor=request.scope2.market_based_factor,
                notes=request.scope2.notes,
            )
            s3 = Scope3Input(
                steel_tonnes=request.scope3.steel_tonnes,
                aluminium_tonnes=request.scope3.aluminium_tonnes,
                concrete_tonnes=request.scope3.concrete_tonnes,
                plastics_tonnes=request.scope3.plastics_tonnes,
                paper_tonnes=request.scope3.paper_tonnes,
                chemicals_tonnes=request.scope3.chemicals_tonnes,
                other_purchased_goods_tco2e=request.scope3.other_purchased_goods_tco2e,
                road_freight_tonne_km=request.scope3.road_freight_tonne_km,
                sea_freight_tonne_km=request.scope3.sea_freight_tonne_km,
                air_freight_tonne_km=request.scope3.air_freight_tonne_km,
                rail_freight_tonne_km=request.scope3.rail_freight_tonne_km,
                air_travel_km=request.scope3.air_travel_km,
                car_travel_km=request.scope3.car_travel_km,
                rail_travel_km=request.scope3.rail_travel_km,
                employees=request.scope3.employees,
                waste_landfill_tonnes=request.scope3.waste_landfill_tonnes,
                waste_incineration_tonnes=request.scope3.waste_incineration_tonnes,
                waste_recycling_tonnes=request.scope3.waste_recycling_tonnes,
                cat2_capital_goods_tco2e=request.scope3.cat2_capital_goods_tco2e,
                cat3_fuel_energy_tco2e=request.scope3.cat3_fuel_energy_tco2e,
                cat5_waste_operations_tco2e=request.scope3.cat5_waste_operations_tco2e,
                cat8_upstream_leased_tco2e=request.scope3.cat8_upstream_leased_tco2e,
                cat9_downstream_transport_tco2e=request.scope3.cat9_downstream_transport_tco2e,
                cat10_processing_sold_products_tco2e=request.scope3.cat10_processing_sold_products_tco2e,
                cat11_use_sold_products_tco2e=request.scope3.cat11_use_sold_products_tco2e,
                cat13_downstream_leased_tco2e=request.scope3.cat13_downstream_leased_tco2e,
                cat14_franchises_tco2e=request.scope3.cat14_franchises_tco2e,
                cat15_investments_tco2e=request.scope3.cat15_investments_tco2e,
                notes=request.scope3.notes,
            )
            report = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: carbon_engine.calculate(
                    scope1=s1,
                    scope2=s2,
                    scope3=s3,
                    company_name=request.company_name,
                    reporting_year=request.reporting_year,
                    employees=request.employees,
                    revenue_meur=request.revenue_meur,
                ),
            )
            return {
                "company_name": report.company_name,
                "reporting_year": report.reporting_year,
                "scope1_total_tco2e": report.scope1_total_tco2e,
                "scope2_location_total_tco2e": report.scope2_location_total_tco2e,
                "scope2_market_total_tco2e": report.scope2_market_total_tco2e,
                "scope3_total_tco2e": report.scope3_total_tco2e,
                "total_tco2e": report.total_tco2e,
                "intensity_per_employee": report.intensity_per_employee,
                "intensity_per_revenue_meur": report.intensity_per_revenue_meur,
                "uncertainty_percent": report.uncertainty_percent,
                "methodology_notes": report.methodology_notes,
                "csrd_article": report.csrd_article,
                "esrs_datapoints": report.esrs_datapoints,
                "breakdown": [
                    {
                        "source": b.source,
                        "category": b.category,
                        "sub_category": b.sub_category,
                        "amount_tco2e": b.amount_tco2e,
                        "unit": b.unit,
                        "factor_used": b.factor_used,
                        "factor_source": b.factor_source,
                    }
                    for b in report.breakdown
                ],
                "metadata": {"request_id": request_id},
            }
        except Exception as e:
            logger.error(f"Error in carbon calculation (request_id={request_id}): {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="Error calculating carbon emissions",
                    error_type="internal",
                    request_id=request_id,
                ).model_dump(),
            )


@router.get("/emission-factors")
def carbon_emission_factors() -> dict[str, Any]:
    """Return the built-in emission factors database (Scope 1, 2, 3)."""
    return {
        "emission_factors": carbon_engine.get_emission_factors(),
        "sources": [
            "IPCC AR6 (2021)",
            "IEA World Energy Statistics 2023",
            "European Environment Agency (EEA) 2022",
            "GHG Protocol Corporate Standard",
        ],
        "metadata": {"unit": "tCO2e per stated input unit"},
    }
