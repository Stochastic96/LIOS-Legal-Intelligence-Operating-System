"""API-level tests for compliance and knowledge-base endpoints."""

from __future__ import annotations

import pytest
import pytest_asyncio


pytestmark = pytest.mark.asyncio


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestApplicabilityEndpoint:
    async def test_large_company_csrd_applicable(self, client) -> None:
        resp = await client.post(
            "/compliance/applicability",
            json={
                "name": "BigCo GmbH",
                "employees": 350,
                "turnover_eur": 55_000_000,
                "balance_sheet_eur": 25_000_000,
                "regulation": "CSRD",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["applies"] is True

    async def test_small_company_csrd_not_applicable(self, client) -> None:
        resp = await client.post(
            "/compliance/applicability",
            json={
                "name": "TinyStartup",
                "employees": 10,
                "turnover_eur": 500_000,
                "balance_sheet_eur": 100_000,
                "regulation": "CSRD",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["applies"] is False

    async def test_invalid_regulation_returns_400(self, client) -> None:
        resp = await client.post(
            "/compliance/applicability",
            json={
                "name": "TestCo",
                "employees": 300,
                "turnover_eur": 50_000_000,
                "balance_sheet_eur": 20_000_000,
                "regulation": "INVALID_REG",
            },
        )
        assert resp.status_code == 400

    async def test_check_all_regulations(self, client) -> None:
        resp = await client.post(
            "/compliance/applicability",
            json={
                "name": "MediumCo",
                "employees": 600,
                "turnover_eur": 200_000_000,
                "balance_sheet_eur": 100_000_000,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) > 0


class TestRoadmapEndpoint:
    async def test_roadmap_generated_for_large_company(self, client) -> None:
        resp = await client.post(
            "/compliance/roadmap",
            json={
                "name": "AcmeCorp",
                "employees": 300,
                "turnover_eur": 60_000_000,
                "balance_sheet_eur": 30_000_000,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company_name"] == "AcmeCorp"
        assert isinstance(data["steps"], list)

    async def test_roadmap_empty_for_micro_company(self, client) -> None:
        resp = await client.post(
            "/compliance/roadmap",
            json={
                "name": "MicroCo",
                "employees": 5,
                "turnover_eur": 100_000,
                "balance_sheet_eur": 50_000,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["steps"] == []


class TestConflictEndpoint:
    async def test_csrd_conflicts_detected_for_germany(self, client) -> None:
        resp = await client.get("/compliance/conflicts", params={"query": "CSRD", "jurisdiction": "DE"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["conflict_count"] >= 1

    async def test_no_conflicts_for_unknown_query(self, client) -> None:
        resp = await client.get("/compliance/conflicts", params={"query": "UNKNOWN_REGULATION_XYZ"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["conflict_count"] == 0


class TestBreakdownEndpoint:
    async def test_csrd_breakdown_available(self, client) -> None:
        resp = await client.get("/compliance/breakdown/CSRD")
        assert resp.status_code == 200
        data = resp.json()
        assert data["regulation"] == "CSRD"
        assert len(data["sections"]) >= 1

    async def test_unknown_regulation_returns_404(self, client) -> None:
        resp = await client.get("/compliance/breakdown/UNKNOWN")
        assert resp.status_code == 404
