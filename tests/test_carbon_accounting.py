"""Tests for the Carbon Accounting Engine."""

from __future__ import annotations

import pytest

from lios.features.carbon_accounting import (
    CarbonAccountingEngine,
    Scope1Input,
    Scope2Input,
    Scope3Input,
    EMISSION_FACTORS,
)


@pytest.fixture
def engine() -> CarbonAccountingEngine:
    return CarbonAccountingEngine()


@pytest.fixture
def empty_inputs():
    return Scope1Input(), Scope2Input(), Scope3Input()


class TestEmissionFactors:
    def test_scope1_factors_present(self):
        assert "natural_gas_mwh" in EMISSION_FACTORS["scope1"]
        assert "diesel_litre" in EMISSION_FACTORS["scope1"]
        assert "coal_tonne" in EMISSION_FACTORS["scope1"]

    def test_scope2_factors_present(self):
        assert "electricity_eu_average_mwh" in EMISSION_FACTORS["scope2"]
        assert "electricity_germany_mwh" in EMISSION_FACTORS["scope2"]
        assert "electricity_france_mwh" in EMISSION_FACTORS["scope2"]

    def test_scope3_factors_present(self):
        assert "steel_tonne" in EMISSION_FACTORS["scope3"]
        assert "road_freight_tonne_km" in EMISSION_FACTORS["scope3"]
        assert "air_travel_km" in EMISSION_FACTORS["scope3"]

    def test_all_factors_positive_or_zero(self):
        for scope, factors in EMISSION_FACTORS.items():
            for key, val in factors.items():
                # Recycling credit may be negative, all others non-negative
                if "recycling" not in key:
                    assert val >= 0, f"{scope}.{key} = {val} should be non-negative"

    def test_france_lower_than_poland(self):
        """France (nuclear) should have much lower electricity emission factor than Poland (coal)."""
        assert EMISSION_FACTORS["scope2"]["electricity_france_mwh"] < EMISSION_FACTORS["scope2"]["electricity_poland_mwh"]


class TestScope1Calculations:
    def test_zero_inputs_give_zero(self, engine):
        s1, s2, s3 = Scope1Input(), Scope2Input(), Scope3Input()
        report = engine.calculate(s1, s2, s3)
        assert report.scope1_total_tco2e == 0.0

    def test_natural_gas_calculation(self, engine):
        s1 = Scope1Input(natural_gas_mwh=1000)
        report = engine.calculate(s1, Scope2Input(), Scope3Input())
        expected = 1000 * EMISSION_FACTORS["scope1"]["natural_gas_mwh"]
        assert abs(report.scope1_total_tco2e - expected) < 0.01

    def test_diesel_calculation(self, engine):
        s1 = Scope1Input(diesel_litres=10000)
        report = engine.calculate(s1, Scope2Input(), Scope3Input())
        expected = 10000 * EMISSION_FACTORS["scope1"]["diesel_litre"]
        assert abs(report.scope1_total_tco2e - expected) < 0.01

    def test_multiple_scope1_sources(self, engine):
        s1 = Scope1Input(natural_gas_mwh=500, diesel_litres=5000, coal_tonnes=10)
        report = engine.calculate(s1, Scope2Input(), Scope3Input())
        expected = (
            500 * EMISSION_FACTORS["scope1"]["natural_gas_mwh"]
            + 5000 * EMISSION_FACTORS["scope1"]["diesel_litre"]
            + 10 * EMISSION_FACTORS["scope1"]["coal_tonne"]
        )
        assert abs(report.scope1_total_tco2e - expected) < 0.01

    def test_process_emissions_passthrough(self, engine):
        s1 = Scope1Input(process_emissions_tco2e=50.0)
        report = engine.calculate(s1, Scope2Input(), Scope3Input())
        assert report.scope1_total_tco2e == 50.0

    def test_breakdown_contains_scope1_entries(self, engine):
        s1 = Scope1Input(natural_gas_mwh=100, diesel_litres=200)
        report = engine.calculate(s1, Scope2Input(), Scope3Input())
        scope1_breakdown = [b for b in report.breakdown if b.category == "scope1"]
        assert len(scope1_breakdown) == 2


class TestScope2Calculations:
    def test_electricity_eu_average(self, engine):
        s2 = Scope2Input(electricity_mwh=1000)
        report = engine.calculate(Scope1Input(), s2, Scope3Input())
        expected = 1000 * EMISSION_FACTORS["scope2"]["electricity_eu_average_mwh"]
        assert abs(report.scope2_location_total_tco2e - expected) < 0.01

    def test_electricity_germany(self, engine):
        s2 = Scope2Input(electricity_mwh=1000, country="Germany")
        report = engine.calculate(Scope1Input(), s2, Scope3Input())
        expected = 1000 * EMISSION_FACTORS["scope2"]["electricity_germany_mwh"]
        assert abs(report.scope2_location_total_tco2e - expected) < 0.01

    def test_market_based_calculation(self, engine):
        s2 = Scope2Input(electricity_mwh=1000, use_market_based=True, market_based_factor=0.050)
        report = engine.calculate(Scope1Input(), s2, Scope3Input())
        assert report.scope2_market_total_tco2e == pytest.approx(50.0, abs=0.01)

    def test_no_market_based_when_not_requested(self, engine):
        s2 = Scope2Input(electricity_mwh=1000, use_market_based=False)
        report = engine.calculate(Scope1Input(), s2, Scope3Input())
        assert report.scope2_market_total_tco2e is None

    def test_district_heat(self, engine):
        s2 = Scope2Input(district_heat_mwh=500)
        report = engine.calculate(Scope1Input(), s2, Scope3Input())
        expected = 500 * EMISSION_FACTORS["scope2"]["district_heat_mwh"]
        assert abs(report.scope2_location_total_tco2e - expected) < 0.01

    def test_unknown_country_falls_back_to_eu_average(self, engine):
        s2_unknown = Scope2Input(electricity_mwh=1000, country="Freedonia")
        s2_eu = Scope2Input(electricity_mwh=1000, country="EU")
        r_unknown = engine.calculate(Scope1Input(), s2_unknown, Scope3Input())
        r_eu = engine.calculate(Scope1Input(), s2_eu, Scope3Input())
        assert r_unknown.scope2_location_total_tco2e == r_eu.scope2_location_total_tco2e


class TestScope3Calculations:
    def test_steel_calculation(self, engine):
        s3 = Scope3Input(steel_tonnes=100)
        report = engine.calculate(Scope1Input(), Scope2Input(), s3)
        expected = 100 * EMISSION_FACTORS["scope3"]["steel_tonne"]
        assert abs(report.scope3_total_tco2e - expected) < 0.01

    def test_air_travel_calculation(self, engine):
        s3 = Scope3Input(air_travel_km=100_000)
        report = engine.calculate(Scope1Input(), Scope2Input(), s3)
        expected = 100_000 * EMISSION_FACTORS["scope3"]["air_travel_km"]
        assert abs(report.scope3_total_tco2e - expected) < 0.01

    def test_commuting_calculation(self, engine):
        s3 = Scope3Input(employees=500)
        report = engine.calculate(Scope1Input(), Scope2Input(), s3)
        expected = 500 * EMISSION_FACTORS["scope3"]["commuting_employee_year"]
        assert abs(report.scope3_total_tco2e - expected) < 0.01

    def test_road_freight(self, engine):
        s3 = Scope3Input(road_freight_tonne_km=1_000_000)
        report = engine.calculate(Scope1Input(), Scope2Input(), s3)
        expected = 1_000_000 * EMISSION_FACTORS["scope3"]["road_freight_tonne_km"]
        assert abs(report.scope3_total_tco2e - expected) < 0.01

    def test_recycling_reduces_total(self, engine):
        """Recycled waste should reduce (or provide negative) Scope 3 emissions."""
        s3_with_recycling = Scope3Input(waste_recycling_tonnes=100)
        s3_without = Scope3Input()
        r_with = engine.calculate(Scope1Input(), Scope2Input(), s3_with_recycling)
        r_without = engine.calculate(Scope1Input(), Scope2Input(), s3_without)
        assert r_with.scope3_total_tco2e <= r_without.scope3_total_tco2e

    def test_direct_tco2e_passthrough(self, engine):
        s3 = Scope3Input(cat15_investments_tco2e=500.0)
        report = engine.calculate(Scope1Input(), Scope2Input(), s3)
        assert report.scope3_total_tco2e == pytest.approx(500.0)


class TestCarbonReport:
    def test_total_is_sum_of_scopes(self, engine):
        s1 = Scope1Input(natural_gas_mwh=1000)
        s2 = Scope2Input(electricity_mwh=2000, country="Germany")
        s3 = Scope3Input(air_travel_km=50000, employees=100)
        report = engine.calculate(s1, s2, s3)
        expected_total = report.scope1_total_tco2e + report.scope2_location_total_tco2e + report.scope3_total_tco2e
        assert abs(report.total_tco2e - expected_total) < 0.01

    def test_intensity_per_employee(self, engine):
        s1 = Scope1Input(natural_gas_mwh=1000)
        report = engine.calculate(s1, Scope2Input(), Scope3Input(), employees=200)
        assert report.intensity_per_employee is not None
        assert report.intensity_per_employee == pytest.approx(report.total_tco2e / 200, rel=0.01)

    def test_intensity_per_revenue(self, engine):
        s1 = Scope1Input(natural_gas_mwh=500)
        report = engine.calculate(s1, Scope2Input(), Scope3Input(), revenue_meur=50.0)
        assert report.intensity_per_revenue_meur is not None
        assert report.intensity_per_revenue_meur == pytest.approx(report.total_tco2e / 50.0, rel=0.01)

    def test_no_intensity_when_not_provided(self, engine):
        report = engine.calculate(Scope1Input(), Scope2Input(), Scope3Input())
        assert report.intensity_per_employee is None
        assert report.intensity_per_revenue_meur is None

    def test_esrs_datapoints_present(self, engine):
        s1 = Scope1Input(natural_gas_mwh=100)
        report = engine.calculate(s1, Scope2Input(), Scope3Input())
        dp = report.esrs_datapoints
        assert "E1-6_scope1_gross_tco2e" in dp
        assert "E1-6_scope2_location_tco2e" in dp
        assert "E1-6_scope3_total_tco2e" in dp
        assert "E1-6_total_tco2e" in dp

    def test_csrd_article_reference(self, engine):
        report = engine.calculate(Scope1Input(), Scope2Input(), Scope3Input())
        assert "ESRS E1" in report.csrd_article

    def test_uncertainty_percent_default(self, engine):
        report = engine.calculate(Scope1Input(), Scope2Input(), Scope3Input())
        assert report.uncertainty_percent == 15.0

    def test_company_name_and_year(self, engine):
        report = engine.calculate(
            Scope1Input(), Scope2Input(), Scope3Input(),
            company_name="TestCorp", reporting_year=2023
        )
        assert report.company_name == "TestCorp"
        assert report.reporting_year == 2023

    def test_breakdown_categories(self, engine):
        s1 = Scope1Input(natural_gas_mwh=100)
        s2 = Scope2Input(electricity_mwh=200)
        s3 = Scope3Input(air_travel_km=10000)
        report = engine.calculate(s1, s2, s3)
        cats = {b.category for b in report.breakdown}
        assert "scope1" in cats
        assert "scope2" in cats
        assert "scope3" in cats

    def test_get_emission_factors(self, engine):
        factors = engine.get_emission_factors()
        assert "scope1" in factors
        assert "scope2" in factors
        assert "scope3" in factors

    def test_estimate_scope3_from_spend(self, engine):
        result = engine.estimate_scope3_from_spend(spend_eur=1_000_000)
        assert result > 0

    def test_comprehensive_calculation(self, engine):
        """End-to-end test with realistic company data."""
        s1 = Scope1Input(
            natural_gas_mwh=2500,
            diesel_litres=15000,
            process_emissions_tco2e=50,
        )
        s2 = Scope2Input(
            electricity_mwh=5000,
            district_heat_mwh=300,
            country="Germany",
            use_market_based=True,
            market_based_factor=0.12,
        )
        s3 = Scope3Input(
            steel_tonnes=200,
            road_freight_tonne_km=2_000_000,
            air_travel_km=500_000,
            employees=750,
            waste_landfill_tonnes=20,
        )
        report = engine.calculate(
            s1, s2, s3,
            company_name="TestMfg GmbH",
            reporting_year=2024,
            employees=750,
            revenue_meur=180.0,
        )
        assert report.total_tco2e > 0
        assert report.scope1_total_tco2e > 0
        assert report.scope2_location_total_tco2e > 0
        assert report.scope3_total_tco2e > 0
        assert report.scope2_market_total_tco2e is not None
        assert report.intensity_per_employee > 0
        assert report.intensity_per_revenue_meur > 0
        assert len(report.breakdown) > 0
