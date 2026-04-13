"""Tests for the seven analytical features."""

from __future__ import annotations

import pytest

from lios.features.applicability_checker import ApplicabilityChecker, ApplicabilityResult
from lios.features.citation_engine import Citation, CitationEngine
from lios.features.compliance_roadmap import ComplianceRoadmap, ComplianceRoadmapGenerator
from lios.features.conflict_mapper import ConflictMap, ConflictMapper
from lios.features.decay_scoring import RegulatoryDecayScorer
from lios.features.jurisdiction_conflict import JurisdictionConflictDetector
from lios.features.legal_breakdown import LegalBreakdown, LegalBreakdownGenerator
from lios.knowledge.regulatory_db import RegulatoryDatabase


@pytest.fixture(scope="module")
def db():
    return RegulatoryDatabase()


# ------------------------------------------------------------------ #
# 1. Applicability Checker
# ------------------------------------------------------------------ #

class TestApplicabilityChecker:
    @pytest.fixture
    def checker(self):
        return ApplicabilityChecker()

    def test_csrd_applicable_large_company(self, checker):
        profile = {"employees": 600, "turnover_eur": 50_000_000, "balance_sheet_eur": 25_000_000}
        result = checker.check_applicability("CSRD", profile)
        assert result.applicable is True

    def test_csrd_not_applicable_small_company(self, checker):
        profile = {"employees": 50, "turnover_eur": 3_000_000, "balance_sheet_eur": 1_000_000}
        result = checker.check_applicability("CSRD", profile)
        assert result.applicable is False

    def test_csrd_applicable_phase2(self, checker):
        # 260 employees + turnover > 40M → large company (2 of 3 criteria)
        profile = {"employees": 260, "turnover_eur": 45_000_000, "balance_sheet_eur": 5_000_000}
        result = checker.check_applicability("CSRD", profile)
        assert result.applicable is True

    def test_csrd_applicable_listed_sme(self, checker):
        profile = {"employees": 100, "turnover_eur": 10_000_000, "listed": True}
        result = checker.check_applicability("CSRD", profile)
        assert result.applicable is True

    def test_sfdr_applicable_financial_sector(self, checker):
        profile = {"employees": 100, "sector": "asset management"}
        result = checker.check_applicability("SFDR", profile)
        assert result.applicable is True

    def test_sfdr_not_applicable_non_financial(self, checker):
        profile = {"employees": 600, "sector": "manufacturing"}
        result = checker.check_applicability("SFDR", profile)
        assert result.applicable is False

    def test_eu_taxonomy_applicable_large_nonfinancial(self, checker):
        profile = {"employees": 600, "turnover_eur": 50_000_000, "sector": "manufacturing"}
        result = checker.check_applicability("EU_TAXONOMY", profile)
        assert result.applicable is True

    def test_result_has_reason(self, checker):
        profile = {"employees": 600}
        result = checker.check_applicability("CSRD", profile)
        assert result.reason
        assert len(result.reason) > 10

    def test_result_has_articles_cited(self, checker):
        profile = {"employees": 600}
        result = checker.check_applicability("CSRD", profile)
        assert isinstance(result.articles_cited, list)
        assert len(result.articles_cited) > 0

    def test_unknown_regulation(self, checker):
        profile = {"employees": 600}
        result = checker.check_applicability("UNKNOWN", profile)
        assert result.applicable is False


# ------------------------------------------------------------------ #
# 2. Citation Engine
# ------------------------------------------------------------------ #

class TestCitationEngine:
    @pytest.fixture
    def engine(self, db):
        return CitationEngine(db)

    def test_get_citations_returns_list(self, engine):
        citations = engine.get_citations("CSRD sustainability reporting")
        assert isinstance(citations, list)

    def test_citations_are_citation_objects(self, engine):
        citations = engine.get_citations("double materiality CSRD")
        for c in citations:
            assert isinstance(c, Citation)

    def test_citations_have_required_fields(self, engine):
        citations = engine.get_citations("CSRD reporting thresholds")
        for c in citations:
            assert c.regulation
            assert c.article_id
            assert c.url.startswith("http")
            assert 0 <= c.relevance_score

    def test_citation_regulation_filter(self, engine):
        citations = engine.get_citations("sustainability reporting", regulations=["CSRD"])
        regs = {c.regulation for c in citations}
        assert regs.issubset({"CSRD"})

    def test_no_duplicate_citations(self, engine):
        citations = engine.get_citations("climate GHG emissions ESRS E1")
        keys = [f"{c.regulation}:{c.article_id}" for c in citations]
        assert len(keys) == len(set(keys))

    def test_empty_query_returns_empty(self, engine):
        citations = engine.get_citations("")
        assert citations == []


# ------------------------------------------------------------------ #
# 3. Compliance Roadmap
# ------------------------------------------------------------------ #

class TestComplianceRoadmap:
    @pytest.fixture
    def gen(self):
        return ComplianceRoadmapGenerator()

    def test_roadmap_returns_dataclass(self, gen, sample_company_profile):
        rm = gen.generate_roadmap(sample_company_profile)
        assert isinstance(rm, ComplianceRoadmap)

    def test_roadmap_has_steps(self, gen, sample_company_profile):
        rm = gen.generate_roadmap(sample_company_profile)
        assert len(rm.steps) > 0

    def test_roadmap_steps_ordered(self, gen, sample_company_profile):
        rm = gen.generate_roadmap(sample_company_profile)
        for i, step in enumerate(rm.steps, start=1):
            assert step.step_number == i

    def test_roadmap_applicable_regulations(self, gen, sample_company_profile):
        rm = gen.generate_roadmap(sample_company_profile)
        assert "CSRD" in rm.applicable_regulations

    def test_roadmap_small_company(self, gen, small_company_profile):
        rm = gen.generate_roadmap(small_company_profile)
        # Small company may have no applicable regs
        assert isinstance(rm.applicable_regulations, list)

    def test_roadmap_financial_company(self, gen, finance_company_profile):
        rm = gen.generate_roadmap(finance_company_profile)
        assert "SFDR" in rm.applicable_regulations

    def test_roadmap_steps_have_priorities(self, gen, sample_company_profile):
        rm = gen.generate_roadmap(sample_company_profile)
        valid_priorities = {"critical", "high", "medium", "low"}
        for step in rm.steps:
            assert step.priority in valid_priorities

    def test_roadmap_has_summary(self, gen, sample_company_profile):
        rm = gen.generate_roadmap(sample_company_profile)
        assert rm.summary
        assert len(rm.summary) > 10


# ------------------------------------------------------------------ #
# 4. Conflict Mapper
# ------------------------------------------------------------------ #

class TestConflictMapper:
    @pytest.fixture
    def mapper(self):
        return ConflictMapper()

    def test_map_conflicts_returns_conflict_map(self, mapper):
        result = mapper.map_conflicts(["Germany"], ["CSRD", "SFDR"])
        assert isinstance(result, ConflictMap)

    def test_conflict_map_matrix_structure(self, mapper):
        result = mapper.map_conflicts(["Germany", "France"], ["CSRD"])
        assert "Germany" in result.matrix
        assert "France" in result.matrix
        assert "CSRD" in result.matrix["Germany"]

    def test_conflict_map_counts(self, mapper):
        result = mapper.map_conflicts(["Germany"], ["CSRD"])
        assert result.total_conflicts >= 1

    def test_conflict_map_summary(self, mapper):
        result = mapper.map_conflicts(["Germany"], ["CSRD"])
        assert result.summary

    def test_conflict_map_empty_jurisdictions(self, mapper):
        result = mapper.map_conflicts([], ["CSRD"])
        assert result.total_conflicts == 0


# ------------------------------------------------------------------ #
# 5. Legal Breakdown
# ------------------------------------------------------------------ #

class TestLegalBreakdown:
    @pytest.fixture
    def gen(self, db):
        return LegalBreakdownGenerator(db)

    def test_breakdown_returns_dataclass(self, gen):
        result = gen.generate_breakdown("reporting", "CSRD")
        assert isinstance(result, LegalBreakdown)

    def test_breakdown_has_summary(self, gen):
        result = gen.generate_breakdown("materiality", "CSRD")
        assert result.summary

    def test_breakdown_has_articles(self, gen):
        result = gen.generate_breakdown("climate", "ESRS")
        assert isinstance(result.key_articles, list)

    def test_breakdown_has_timeline(self, gen):
        result = gen.generate_breakdown("reporting timeline", "CSRD")
        assert isinstance(result.timeline, list)
        assert len(result.timeline) > 0

    def test_breakdown_has_penalties(self, gen):
        result = gen.generate_breakdown("penalties", "CSRD")
        assert isinstance(result.penalties, list)
        assert len(result.penalties) > 0

    def test_breakdown_unknown_regulation(self, gen):
        result = gen.generate_breakdown("reporting", "UNKNOWN_REG")
        assert "not found" in result.summary.lower()

    def test_breakdown_obligations_list(self, gen):
        result = gen.generate_breakdown("reporting obligations", "CSRD")
        assert isinstance(result.obligations, list)
