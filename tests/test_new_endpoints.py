"""Integration tests for the new LIOS API endpoints (carbon, supply chain, materiality)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lios.api.routes import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Carbon Accounting API
# ---------------------------------------------------------------------------

class TestCarbonCalculateEndpoint:
    def test_calculate_basic(self, client):
        resp = client.post("/api/carbon/calculate", json={
            "company_name": "TestCorp",
            "reporting_year": 2024,
            "scope1": {"natural_gas_mwh": 1000},
            "scope2": {"electricity_mwh": 2000, "country": "Germany"},
            "scope3": {"air_travel_km": 100000, "employees": 200},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["scope1_total_tco2e"] > 0
        assert data["scope2_location_total_tco2e"] > 0
        assert data["scope3_total_tco2e"] > 0
        assert data["total_tco2e"] > 0

    def test_calculate_returns_esrs_datapoints(self, client):
        resp = client.post("/api/carbon/calculate", json={
            "scope1": {"natural_gas_mwh": 500},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "esrs_datapoints" in data
        assert "E1-6_scope1_gross_tco2e" in data["esrs_datapoints"]

    def test_calculate_returns_breakdown(self, client):
        resp = client.post("/api/carbon/calculate", json={
            "scope1": {"natural_gas_mwh": 500, "diesel_litres": 1000},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "breakdown" in data
        assert len(data["breakdown"]) >= 2

    def test_calculate_with_intensity(self, client):
        resp = client.post("/api/carbon/calculate", json={
            "company_name": "Acme",
            "employees": 300,
            "revenue_meur": 80.0,
            "scope1": {"natural_gas_mwh": 200},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intensity_per_employee"] is not None
        assert data["intensity_per_revenue_meur"] is not None

    def test_calculate_market_based_scope2(self, client):
        resp = client.post("/api/carbon/calculate", json={
            "scope2": {
                "electricity_mwh": 1000,
                "country": "Germany",
                "use_market_based": True,
                "market_based_factor": 0.05,
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["scope2_market_total_tco2e"] is not None
        assert data["scope2_market_total_tco2e"] == pytest.approx(50.0, abs=0.1)

    def test_calculate_all_zeros_returns_zero(self, client):
        resp = client.post("/api/carbon/calculate", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tco2e"] == 0.0

    def test_calculate_returns_methodology_notes(self, client):
        resp = client.post("/api/carbon/calculate", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "methodology_notes" in data
        assert len(data["methodology_notes"]) > 0

    def test_calculate_returns_csrd_article(self, client):
        resp = client.post("/api/carbon/calculate", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "csrd_article" in data
        assert "ESRS E1" in data["csrd_article"]

    def test_calculate_has_metadata(self, client):
        resp = client.post("/api/carbon/calculate", json={})
        assert resp.status_code == 200
        assert "metadata" in resp.json()
        assert "request_id" in resp.json()["metadata"]


class TestCarbonEmissionFactorsEndpoint:
    def test_emission_factors_200(self, client):
        resp = client.get("/api/carbon/emission-factors")
        assert resp.status_code == 200

    def test_emission_factors_has_three_scopes(self, client):
        resp = client.get("/api/carbon/emission-factors")
        data = resp.json()
        assert "scope1" in data["emission_factors"]
        assert "scope2" in data["emission_factors"]
        assert "scope3" in data["emission_factors"]

    def test_emission_factors_has_sources(self, client):
        resp = client.get("/api/carbon/emission-factors")
        assert "sources" in resp.json()
        assert len(resp.json()["sources"]) > 0


# ---------------------------------------------------------------------------
# Supply Chain API
# ---------------------------------------------------------------------------

class TestSupplierEndpoints:
    def test_add_supplier_201(self, client):
        resp = client.post("/api/supply-chain/add-supplier", json={
            "name": "TestSupplier",
            "country": "Germany",
            "sector": "manufacturing",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "supplier_id" in data
        assert data["name"] == "TestSupplier"

    def test_add_supplier_with_esg_scores(self, client):
        resp = client.post("/api/supply-chain/add-supplier", json={
            "name": "ESGSupplier",
            "country": "France",
            "sector": "services",
            "environmental_score": 75,
            "social_score": 80,
            "governance_score": 70,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "esg_scores" in data
        assert data["esg_scores"]["environmental"] == 75.0
        assert data["esg_scores"]["composite"] > 0

    def test_add_supplier_validation_error_missing_name(self, client):
        resp = client.post("/api/supply-chain/add-supplier", json={
            "country": "Germany",
            "sector": "manufacturing",
        })
        assert resp.status_code == 422

    def test_add_supplier_validation_error_missing_country(self, client):
        resp = client.post("/api/supply-chain/add-supplier", json={
            "name": "Test",
            "sector": "manufacturing",
        })
        assert resp.status_code == 422

    def test_list_suppliers(self, client):
        # Add a supplier first
        client.post("/api/supply-chain/add-supplier", json={
            "name": "ListTestSupplier",
            "country": "Germany",
            "sector": "software",
        })
        resp = client.get("/api/supply-chain/suppliers")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "suppliers" in data
        assert data["total"] >= 1

    def test_risk_assessment_endpoint(self, client):
        client.post("/api/supply-chain/add-supplier", json={
            "name": "RiskTestSupplier",
            "country": "Bangladesh",
            "sector": "textile",
            "environmental_score": 30,
            "social_score": 25,
        })
        resp = client.get("/api/supply-chain/risk-assessment")
        assert resp.status_code == 200
        data = resp.json()
        assert "portfolio_summary" in data
        assert "supplier_assessments" in data

    def test_risk_assessment_portfolio_has_counts(self, client):
        resp = client.get("/api/supply-chain/risk-assessment")
        assert resp.status_code == 200
        p = resp.json()["portfolio_summary"]
        assert "total_suppliers" in p
        assert "critical_count" in p
        assert "high_count" in p
        assert "medium_count" in p
        assert "low_count" in p

    def test_due_diligence_checklist(self, client):
        resp = client.get("/api/supply-chain/due-diligence-checklist")
        assert resp.status_code == 200
        data = resp.json()
        assert "checklist" in data
        assert len(data["checklist"]) > 0
        assert "csrd_reference" in data


# ---------------------------------------------------------------------------
# Double Materiality API
# ---------------------------------------------------------------------------

class TestMaterialityEndpoints:
    def test_esrs_topics_endpoint(self, client):
        resp = client.get("/api/impact/esrs-topics")
        assert resp.status_code == 200
        data = resp.json()
        assert "topics" in data
        assert "E1" in data["topics"]
        assert "G1" in data["topics"]

    def test_materiality_template_manufacturing(self, client):
        resp = client.get("/api/impact/materiality-template?sector=manufacturing")
        assert resp.status_code == 200
        data = resp.json()
        assert "topic_inputs" in data
        assert len(data["topic_inputs"]) > 0
        assert data["sector"] == "manufacturing"

    def test_materiality_template_finance(self, client):
        resp = client.get("/api/impact/materiality-template?sector=finance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sector"] == "finance"

    def test_materiality_assessment_basic(self, client):
        resp = client.post("/api/impact/materiality", json={
            "company_profile": {"name": "TestCorp", "sector": "manufacturing"},
            "topics": [
                {
                    "esrs_code": "E1",
                    "sub_topic": "GHG emissions",
                    "impact_severity": 4,
                    "impact_scale": 4,
                    "impact_likelihood": 4,
                    "financial_likelihood": 4,
                    "financial_magnitude": 4,
                    "financial_time_horizon": "short",
                }
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "material_topics" in data
        assert "assessed_topics" in data
        assert len(data["assessed_topics"]) == 1

    def test_materiality_assessment_all_topics(self, client):
        from lios.features.materiality import ESRS_TOPICS
        topics = [
            {
                "esrs_code": code,
                "sub_topic": meta["topic"],
                "impact_severity": 3,
                "impact_scale": 3,
                "impact_likelihood": 3,
                "financial_likelihood": 3,
                "financial_magnitude": 3,
                "financial_time_horizon": "medium",
            }
            for code, meta in ESRS_TOPICS.items()
        ]
        resp = client.post("/api/impact/materiality", json={
            "company_profile": {"name": "LargeCorp", "sector": "manufacturing"},
            "topics": topics,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["assessed_topics"]) == len(ESRS_TOPICS)

    def test_materiality_assessment_has_csrd_refs(self, client):
        resp = client.post("/api/impact/materiality", json={
            "company_profile": {"name": "TestCorp"},
            "topics": [{
                "esrs_code": "E1", "impact_severity": 4, "impact_scale": 4,
                "impact_likelihood": 4, "financial_likelihood": 4,
                "financial_magnitude": 4, "financial_time_horizon": "short",
            }],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "csrd_article_references" in data
        assert len(data["csrd_article_references"]) > 0

    def test_materiality_assessment_has_recommended_disclosures(self, client):
        resp = client.post("/api/impact/materiality", json={
            "company_profile": {"name": "TestCorp"},
            "topics": [{
                "esrs_code": "E1", "impact_severity": 5, "impact_scale": 5,
                "impact_likelihood": 5, "financial_likelihood": 5,
                "financial_magnitude": 5, "financial_time_horizon": "short",
            }],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_disclosures" in data
        assert any("ESRS 2" in d for d in data["recommended_disclosures"])

    def test_materiality_validation_empty_topics(self, client):
        resp = client.post("/api/impact/materiality", json={
            "company_profile": {"name": "TestCorp"},
            "topics": [],
        })
        assert resp.status_code == 422

    def test_materiality_invalid_time_horizon(self, client):
        resp = client.post("/api/impact/materiality", json={
            "company_profile": {"name": "TestCorp"},
            "topics": [{
                "esrs_code": "E1", "impact_severity": 3, "impact_scale": 3,
                "impact_likelihood": 3, "financial_likelihood": 3,
                "financial_magnitude": 3,
                "financial_time_horizon": "invalid_value",
            }],
        })
        assert resp.status_code == 422

    def test_materiality_mandatory_topics_always_returned(self, client):
        resp = client.post("/api/impact/materiality", json={
            "company_profile": {"name": "TestCorp"},
            "topics": [{
                "esrs_code": "E1", "impact_severity": 1, "impact_scale": 1,
                "impact_likelihood": 1, "financial_likelihood": 1,
                "financial_magnitude": 1, "financial_time_horizon": "long",
            }],
        })
        assert resp.status_code == 200
        data = resp.json()
        # ESRS 1 & 2 always mandatory
        assert "ESRS 1" in data.get("mandatory_topics", [])
        assert "ESRS 2" in data.get("mandatory_topics", [])

    def test_materiality_has_next_steps(self, client):
        resp = client.post("/api/impact/materiality", json={
            "company_profile": {"name": "TestCorp"},
            "topics": [{
                "esrs_code": "E1", "impact_severity": 4, "impact_scale": 4,
                "impact_likelihood": 4, "financial_likelihood": 4,
                "financial_magnitude": 4, "financial_time_horizon": "short",
            }],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "next_steps" in data
        assert len(data["next_steps"]) > 0


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestDashboardEndpoint:
    def test_dashboard_200(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_dashboard_returns_html(self, client):
        resp = client.get("/dashboard")
        assert "text/html" in resp.headers["content-type"]

    def test_dashboard_has_key_sections(self, client):
        resp = client.get("/dashboard")
        html = resp.text
        assert "Carbon Calculator" in html
        assert "Supply Chain" in html
        assert "Materiality" in html
        assert "CSRD" in html

    def test_dashboard_has_api_calls(self, client):
        resp = client.get("/dashboard")
        html = resp.text
        assert "/api/carbon/calculate" in html
        assert "/api/supply-chain/add-supplier" in html
        assert "/api/impact/materiality" in html
