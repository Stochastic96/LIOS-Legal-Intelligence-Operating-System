"""GHG Protocol-compliant Carbon Accounting Engine for CSRD reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Emission factors (tCO2e per unit)
# Sources: IPCC AR6, EU ETS, GHG Protocol, IEA 2023
# ---------------------------------------------------------------------------

EMISSION_FACTORS: dict[str, dict[str, float]] = {
    # Scope 1 – direct combustion (tCO2e per MWh or per tonne fuel)
    "scope1": {
        "natural_gas_mwh": 0.202,       # tCO2e/MWh (EU average)
        "diesel_litre": 0.002687,        # tCO2e/litre
        "petrol_litre": 0.002392,        # tCO2e/litre
        "coal_tonne": 2.42,              # tCO2e/tonne
        "fuel_oil_litre": 0.002968,      # tCO2e/litre
        "lpg_litre": 0.001631,           # tCO2e/litre
        "biomass_tonne": 0.0,            # Biogenic (reported separately per GHG Protocol)
        "process_emissions_tco2e": 1.0,  # Direct process emissions (1:1 factor)
    },
    # Scope 2 – purchased electricity/heat (tCO2e per MWh)
    "scope2": {
        "electricity_eu_average_mwh": 0.276,     # tCO2e/MWh (EU27 2022, EEA)
        "electricity_germany_mwh": 0.364,
        "electricity_france_mwh": 0.052,          # Nuclear-heavy
        "electricity_poland_mwh": 0.773,
        "electricity_sweden_mwh": 0.013,
        "electricity_uk_mwh": 0.207,
        "electricity_us_mwh": 0.386,
        "district_heat_mwh": 0.150,               # EU average district heating
        "steam_mwh": 0.180,
    },
    # Scope 3 – value chain (tCO2e per unit, varied units below)
    "scope3": {
        # Cat 1 – Purchased goods & services (per tonne material)
        "steel_tonne": 1.85,
        "aluminium_tonne": 8.24,
        "concrete_tonne": 0.13,
        "plastics_tonne": 3.14,
        "paper_tonne": 0.94,
        "chemicals_tonne": 2.10,
        # Cat 4 – Upstream transportation (tCO2e per tonne-km)
        "road_freight_tonne_km": 0.000096,
        "sea_freight_tonne_km": 0.000011,
        "air_freight_tonne_km": 0.000601,
        "rail_freight_tonne_km": 0.000028,
        # Cat 6 – Business travel (tCO2e per passenger-km)
        "air_travel_km": 0.000255,
        "car_travel_km": 0.000192,
        "rail_travel_km": 0.000041,
        # Cat 7 – Employee commuting (tCO2e per employee per year, EU avg)
        "commuting_employee_year": 1.20,
        # Cat 11 – Use of sold products (per unit sold, sector average)
        "product_use_unit": 0.0,  # Must be calculated per-product
        # Cat 12 – End-of-life treatment (per tonne product)
        "waste_landfill_tonne": 0.587,
        "waste_incineration_tonne": 1.27,
        "waste_recycling_tonne": -0.150,  # Avoided emissions credit
    },
}

# GHG global warming potential multipliers (AR6, 100-year horizon)
GWP_FACTORS: dict[str, float] = {
    "CO2": 1.0,
    "CH4": 27.9,
    "N2O": 273.0,
    "HFCs": 675.0,   # representative blend
    "PFCs": 7380.0,  # representative blend
    "SF6": 24300.0,
    "NF3": 17400.0,
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Scope1Input:
    """Direct emission sources owned or controlled by the company."""
    natural_gas_mwh: float = 0.0
    diesel_litres: float = 0.0
    petrol_litres: float = 0.0
    coal_tonnes: float = 0.0
    fuel_oil_litres: float = 0.0
    lpg_litres: float = 0.0
    process_emissions_tco2e: float = 0.0
    notes: str = ""


@dataclass
class Scope2Input:
    """Indirect emissions from purchased energy."""
    electricity_mwh: float = 0.0
    district_heat_mwh: float = 0.0
    steam_mwh: float = 0.0
    country: str = "EU"
    use_market_based: bool = False
    market_based_factor: float | None = None  # tCO2e/MWh if known
    notes: str = ""


@dataclass
class Scope3Input:
    """Value chain emissions (15 categories per GHG Protocol)."""
    # Category 1 – Purchased goods & services
    steel_tonnes: float = 0.0
    aluminium_tonnes: float = 0.0
    concrete_tonnes: float = 0.0
    plastics_tonnes: float = 0.0
    paper_tonnes: float = 0.0
    chemicals_tonnes: float = 0.0
    other_purchased_goods_tco2e: float = 0.0  # spend-based or supplier-specific

    # Category 4 – Upstream transportation
    road_freight_tonne_km: float = 0.0
    sea_freight_tonne_km: float = 0.0
    air_freight_tonne_km: float = 0.0
    rail_freight_tonne_km: float = 0.0

    # Category 6 – Business travel
    air_travel_km: float = 0.0
    car_travel_km: float = 0.0
    rail_travel_km: float = 0.0

    # Category 7 – Employee commuting
    employees: int = 0

    # Category 12 – End-of-life
    waste_landfill_tonnes: float = 0.0
    waste_incineration_tonnes: float = 0.0
    waste_recycling_tonnes: float = 0.0

    # Other categories (direct tCO2e inputs)
    cat2_capital_goods_tco2e: float = 0.0
    cat3_fuel_energy_tco2e: float = 0.0
    cat5_waste_operations_tco2e: float = 0.0
    cat8_upstream_leased_tco2e: float = 0.0
    cat9_downstream_transport_tco2e: float = 0.0
    cat10_processing_sold_products_tco2e: float = 0.0
    cat11_use_sold_products_tco2e: float = 0.0
    cat13_downstream_leased_tco2e: float = 0.0
    cat14_franchises_tco2e: float = 0.0
    cat15_investments_tco2e: float = 0.0
    notes: str = ""


@dataclass
class EmissionBreakdown:
    """Detailed line-item breakdown of emissions."""
    source: str
    category: str   # "scope1" | "scope2" | "scope3"
    sub_category: str
    amount_tco2e: float
    unit: str
    factor_used: float
    factor_source: str = "GHG Protocol / IEA 2023"


@dataclass
class CarbonReport:
    """CSRD-aligned carbon accounting report."""
    company_name: str
    reporting_year: int
    scope1_total_tco2e: float
    scope2_location_total_tco2e: float
    scope2_market_total_tco2e: float | None
    scope3_total_tco2e: float
    total_tco2e: float
    intensity_per_employee: float | None
    intensity_per_revenue_meur: float | None
    breakdown: list[EmissionBreakdown] = field(default_factory=list)
    uncertainty_percent: float = 15.0  # Default ±15% per GHG Protocol guidance
    methodology_notes: str = ""
    csrd_article: str = "ESRS E1 – Climate Change"
    esrs_datapoints: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class CarbonAccountingEngine:
    """GHG Protocol-compliant carbon accounting for Scope 1, 2, and 3 emissions.

    Produces CSRD/ESRS E1-aligned output including:
    - tCO2e totals per scope
    - Intensity metrics (per employee, per revenue)
    - ESRS E1 required data-points
    - Uncertainty estimate
    """

    def calculate(
        self,
        scope1: Scope1Input,
        scope2: Scope2Input,
        scope3: Scope3Input,
        company_name: str = "Company",
        reporting_year: int = 2024,
        employees: int | None = None,
        revenue_meur: float | None = None,
    ) -> CarbonReport:
        """Calculate total GHG emissions and return a CSRD-aligned report."""
        breakdown: list[EmissionBreakdown] = []

        # --- Scope 1 ---
        s1_total, s1_breakdown = self._calc_scope1(scope1)
        breakdown.extend(s1_breakdown)

        # --- Scope 2 ---
        s2_loc, s2_mkt, s2_breakdown = self._calc_scope2(scope2)
        breakdown.extend(s2_breakdown)

        # --- Scope 3 ---
        s3_total, s3_breakdown = self._calc_scope3(scope3)
        breakdown.extend(s3_breakdown)

        # Use location-based Scope 2 for total (market-based disclosed separately)
        total = s1_total + s2_loc + s3_total

        # Intensity metrics
        eff_employees = employees or scope3.employees or None
        intensity_per_employee = (total / eff_employees) if eff_employees else None
        intensity_per_rev = (total / revenue_meur) if revenue_meur else None

        # ESRS E1 mandatory data-points (DR E1-6)
        esrs_dp: dict[str, Any] = {
            "E1-6_scope1_gross_tco2e": round(s1_total, 2),
            "E1-6_scope2_location_tco2e": round(s2_loc, 2),
            "E1-6_scope2_market_tco2e": round(s2_mkt, 2) if s2_mkt is not None else None,
            "E1-6_scope3_total_tco2e": round(s3_total, 2),
            "E1-6_total_tco2e": round(total, 2),
            "E1-6_ghg_intensity_revenue": round(intensity_per_rev, 4) if intensity_per_rev else None,
            "E1-6_ghg_intensity_employees": round(intensity_per_employee, 2) if intensity_per_employee else None,
        }

        return CarbonReport(
            company_name=company_name,
            reporting_year=reporting_year,
            scope1_total_tco2e=round(s1_total, 2),
            scope2_location_total_tco2e=round(s2_loc, 2),
            scope2_market_total_tco2e=round(s2_mkt, 2) if s2_mkt is not None else None,
            scope3_total_tco2e=round(s3_total, 2),
            total_tco2e=round(total, 2),
            intensity_per_employee=round(intensity_per_employee, 2) if intensity_per_employee else None,
            intensity_per_revenue_meur=round(intensity_per_rev, 4) if intensity_per_rev else None,
            breakdown=breakdown,
            uncertainty_percent=15.0,
            methodology_notes=(
                "Calculated using GHG Protocol Corporate Standard. "
                "Emission factors sourced from IEA 2023, EEA 2022, and IPCC AR6. "
                "Scope 2 uses location-based method as primary; market-based disclosed where available. "
                "Scope 3 completeness: categories with data collected explicitly; "
                "categories without data are disclosed as not assessed."
            ),
            csrd_article="ESRS E1 – Climate Change (DR E1-6)",
            esrs_datapoints=esrs_dp,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calc_scope1(
        self, inp: Scope1Input
    ) -> tuple[float, list[EmissionBreakdown]]:
        f = EMISSION_FACTORS["scope1"]
        items: list[tuple[str, float, float, str]] = [
            ("Natural gas combustion", inp.natural_gas_mwh, f["natural_gas_mwh"], "MWh"),
            ("Diesel combustion", inp.diesel_litres, f["diesel_litre"], "litres"),
            ("Petrol combustion", inp.petrol_litres, f["petrol_litre"], "litres"),
            ("Coal combustion", inp.coal_tonnes, f["coal_tonne"], "tonnes"),
            ("Fuel oil combustion", inp.fuel_oil_litres, f["fuel_oil_litre"], "litres"),
            ("LPG combustion", inp.lpg_litres, f["lpg_litre"], "litres"),
            ("Process emissions", inp.process_emissions_tco2e, f["process_emissions_tco2e"], "tCO2e"),
        ]
        breakdown: list[EmissionBreakdown] = []
        total = 0.0
        for source, qty, factor, unit in items:
            if qty > 0:
                amount = qty * factor
                total += amount
                breakdown.append(EmissionBreakdown(
                    source=source,
                    category="scope1",
                    sub_category="direct_combustion",
                    amount_tco2e=round(amount, 4),
                    unit=unit,
                    factor_used=factor,
                ))
        return total, breakdown

    def _calc_scope2(
        self, inp: Scope2Input
    ) -> tuple[float, float | None, list[EmissionBreakdown]]:
        f = EMISSION_FACTORS["scope2"]
        country_key = f"electricity_{inp.country.lower().replace(' ', '_')}_mwh"
        loc_factor = f.get(country_key, f["electricity_eu_average_mwh"])

        loc_total = 0.0
        mkt_total: float | None = None
        breakdown: list[EmissionBreakdown] = []

        if inp.electricity_mwh > 0:
            loc_amount = inp.electricity_mwh * loc_factor
            loc_total += loc_amount
            breakdown.append(EmissionBreakdown(
                source="Purchased electricity (location-based)",
                category="scope2",
                sub_category="electricity",
                amount_tco2e=round(loc_amount, 4),
                unit="MWh",
                factor_used=loc_factor,
                factor_source=f"EEA 2022 – {inp.country}",
            ))
            if inp.use_market_based and inp.market_based_factor is not None:
                mkt_amount = inp.electricity_mwh * inp.market_based_factor
                mkt_total = mkt_amount
                breakdown.append(EmissionBreakdown(
                    source="Purchased electricity (market-based)",
                    category="scope2",
                    sub_category="electricity_market",
                    amount_tco2e=round(mkt_amount, 4),
                    unit="MWh",
                    factor_used=inp.market_based_factor,
                    factor_source="Supplier EAC / residual mix",
                ))

        if inp.district_heat_mwh > 0:
            amount = inp.district_heat_mwh * f["district_heat_mwh"]
            loc_total += amount
            breakdown.append(EmissionBreakdown(
                source="District heating",
                category="scope2",
                sub_category="heat",
                amount_tco2e=round(amount, 4),
                unit="MWh",
                factor_used=f["district_heat_mwh"],
            ))

        if inp.steam_mwh > 0:
            amount = inp.steam_mwh * f["steam_mwh"]
            loc_total += amount
            breakdown.append(EmissionBreakdown(
                source="Purchased steam",
                category="scope2",
                sub_category="steam",
                amount_tco2e=round(amount, 4),
                unit="MWh",
                factor_used=f["steam_mwh"],
            ))

        return loc_total, mkt_total, breakdown

    def _calc_scope3(
        self, inp: Scope3Input
    ) -> tuple[float, list[EmissionBreakdown]]:
        f = EMISSION_FACTORS["scope3"]
        total = 0.0
        breakdown: list[EmissionBreakdown] = []

        # Category 1 – purchased goods
        cat1_items = [
            ("Steel – purchased goods", inp.steel_tonnes, f["steel_tonne"], "tonnes"),
            ("Aluminium – purchased goods", inp.aluminium_tonnes, f["aluminium_tonne"], "tonnes"),
            ("Concrete – purchased goods", inp.concrete_tonnes, f["concrete_tonne"], "tonnes"),
            ("Plastics – purchased goods", inp.plastics_tonnes, f["plastics_tonne"], "tonnes"),
            ("Paper – purchased goods", inp.paper_tonnes, f["paper_tonne"], "tonnes"),
            ("Chemicals – purchased goods", inp.chemicals_tonnes, f["chemicals_tonne"], "tonnes"),
        ]
        for source, qty, factor, unit in cat1_items:
            if qty > 0:
                amount = qty * factor
                total += amount
                breakdown.append(EmissionBreakdown(
                    source=source, category="scope3", sub_category="cat1_purchased_goods",
                    amount_tco2e=round(amount, 4), unit=unit, factor_used=factor,
                ))
        if inp.other_purchased_goods_tco2e > 0:
            total += inp.other_purchased_goods_tco2e
            breakdown.append(EmissionBreakdown(
                source="Other purchased goods (supplier-specific / spend-based)",
                category="scope3", sub_category="cat1_purchased_goods",
                amount_tco2e=round(inp.other_purchased_goods_tco2e, 4),
                unit="tCO2e", factor_used=1.0,
            ))

        # Category 2 – capital goods
        if inp.cat2_capital_goods_tco2e > 0:
            total += inp.cat2_capital_goods_tco2e
            breakdown.append(EmissionBreakdown(
                source="Capital goods", category="scope3", sub_category="cat2_capital_goods",
                amount_tco2e=round(inp.cat2_capital_goods_tco2e, 4),
                unit="tCO2e", factor_used=1.0,
            ))

        # Category 3 – fuel & energy (upstream)
        if inp.cat3_fuel_energy_tco2e > 0:
            total += inp.cat3_fuel_energy_tco2e
            breakdown.append(EmissionBreakdown(
                source="Fuel & energy activities (upstream)", category="scope3",
                sub_category="cat3_fuel_energy",
                amount_tco2e=round(inp.cat3_fuel_energy_tco2e, 4),
                unit="tCO2e", factor_used=1.0,
            ))

        # Category 4 – upstream transport
        trans_items = [
            ("Road freight – upstream transport", inp.road_freight_tonne_km, f["road_freight_tonne_km"], "tonne-km"),
            ("Sea freight – upstream transport", inp.sea_freight_tonne_km, f["sea_freight_tonne_km"], "tonne-km"),
            ("Air freight – upstream transport", inp.air_freight_tonne_km, f["air_freight_tonne_km"], "tonne-km"),
            ("Rail freight – upstream transport", inp.rail_freight_tonne_km, f["rail_freight_tonne_km"], "tonne-km"),
        ]
        for source, qty, factor, unit in trans_items:
            if qty > 0:
                amount = qty * factor
                total += amount
                breakdown.append(EmissionBreakdown(
                    source=source, category="scope3", sub_category="cat4_upstream_transport",
                    amount_tco2e=round(amount, 4), unit=unit, factor_used=factor,
                ))

        # Category 5 – waste in operations
        waste_ops_items = [
            ("Waste to landfill", inp.waste_landfill_tonnes, f["waste_landfill_tonne"], "tonnes"),
            ("Waste incinerated", inp.waste_incineration_tonnes, f["waste_incineration_tonne"], "tonnes"),
            ("Waste recycled (avoided)", inp.waste_recycling_tonnes, f["waste_recycling_tonne"], "tonnes"),
        ]
        for source, qty, factor, unit in waste_ops_items:
            if qty > 0:
                amount = qty * factor
                total += amount
                breakdown.append(EmissionBreakdown(
                    source=source, category="scope3", sub_category="cat5_waste_operations",
                    amount_tco2e=round(amount, 4), unit=unit, factor_used=factor,
                ))

        if inp.cat5_waste_operations_tco2e > 0:
            total += inp.cat5_waste_operations_tco2e
            breakdown.append(EmissionBreakdown(
                source="Waste in operations (other)", category="scope3",
                sub_category="cat5_waste_operations",
                amount_tco2e=round(inp.cat5_waste_operations_tco2e, 4),
                unit="tCO2e", factor_used=1.0,
            ))

        # Category 6 – business travel
        travel_items = [
            ("Air travel – business", inp.air_travel_km, f["air_travel_km"], "km"),
            ("Car travel – business", inp.car_travel_km, f["car_travel_km"], "km"),
            ("Rail travel – business", inp.rail_travel_km, f["rail_travel_km"], "km"),
        ]
        for source, qty, factor, unit in travel_items:
            if qty > 0:
                amount = qty * factor
                total += amount
                breakdown.append(EmissionBreakdown(
                    source=source, category="scope3", sub_category="cat6_business_travel",
                    amount_tco2e=round(amount, 4), unit=unit, factor_used=factor,
                ))

        # Category 7 – employee commuting
        if inp.employees > 0:
            amount = inp.employees * f["commuting_employee_year"]
            total += amount
            breakdown.append(EmissionBreakdown(
                source=f"Employee commuting ({inp.employees} employees)",
                category="scope3", sub_category="cat7_employee_commuting",
                amount_tco2e=round(amount, 4), unit="employees × year", factor_used=f["commuting_employee_year"],
            ))

        # Remaining categories (direct tCO2e inputs)
        direct_cats = [
            ("cat8_upstream_leased_tco2e", "Upstream leased assets", "cat8_upstream_leased"),
            ("cat9_downstream_transport_tco2e", "Downstream transport & distribution", "cat9_downstream_transport"),
            ("cat10_processing_sold_products_tco2e", "Processing of sold products", "cat10_processing"),
            ("cat11_use_sold_products_tco2e", "Use of sold products", "cat11_use_sold"),
            ("cat13_downstream_leased_tco2e", "Downstream leased assets", "cat13_downstream_leased"),
            ("cat14_franchises_tco2e", "Franchises", "cat14_franchises"),
            ("cat15_investments_tco2e", "Investments", "cat15_investments"),
        ]
        for attr, label, sub_cat in direct_cats:
            qty = getattr(inp, attr, 0.0)
            if qty > 0:
                total += qty
                breakdown.append(EmissionBreakdown(
                    source=label, category="scope3", sub_category=sub_cat,
                    amount_tco2e=round(qty, 4), unit="tCO2e", factor_used=1.0,
                ))

        return total, breakdown

    def get_emission_factors(self) -> dict[str, dict[str, float]]:
        """Return the built-in emission factors database."""
        return EMISSION_FACTORS

    def estimate_scope3_from_spend(
        self, spend_eur: float, sector_intensity: float = 0.35
    ) -> float:
        """Estimate Scope 3 Cat 1 emissions from procurement spend.

        Args:
            spend_eur: Annual procurement spend in EUR.
            sector_intensity: tCO2e per EUR spent (default 0.35 = EU manufacturing avg).

        Returns:
            Estimated tCO2e.
        """
        return spend_eur * sector_intensity / 1000.0  # convert EUR to kEUR then apply factor
