"""Tests for the Supply Chain Due Diligence module."""

from __future__ import annotations

import pytest

from lios.features.supply_chain import (
    SupplyChainDueDiligenceEngine,
    RiskLevel,
    AuditStatus,
    CSRD_DUE_DILIGENCE_CHECKLIST,
    COUNTRY_RISK_INDEX,
    SECTOR_RISK_MULTIPLIER,
)


@pytest.fixture
def engine() -> SupplyChainDueDiligenceEngine:
    return SupplyChainDueDiligenceEngine()


@pytest.fixture
def engine_with_suppliers(engine) -> SupplyChainDueDiligenceEngine:
    """Engine pre-loaded with sample suppliers."""
    engine.add_supplier(
        name="GreenTech GmbH",
        country="Germany",
        sector="software",
        tier=1,
        environmental_score=80,
        social_score=75,
        governance_score=85,
        data_quality=90,
        annual_spend_eur=500_000,
        employees=200,
        certifications=["ISO 14001"],
    )
    engine.add_supplier(
        name="TextCo Ltd",
        country="Bangladesh",
        sector="textile",
        tier=1,
        environmental_score=30,
        social_score=25,
        governance_score=40,
        data_quality=30,
        annual_spend_eur=1_200_000,
        employees=5000,
    )
    engine.add_supplier(
        name="MidSupplier SA",
        country="Spain",
        sector="manufacturing",
        tier=2,
        environmental_score=55,
        social_score=60,
        governance_score=65,
        data_quality=60,
        annual_spend_eur=300_000,
        employees=150,
    )
    return engine


class TestSupplierRegistration:
    def test_add_supplier_returns_supplier(self, engine):
        supplier = engine.add_supplier(
            name="Acme Corp", country="France", sector="manufacturing", tier=1,
            environmental_score=60, social_score=70, governance_score=65,
        )
        assert supplier.name == "Acme Corp"
        assert supplier.country == "France"
        assert supplier.sector == "manufacturing"
        assert supplier.tier == 1

    def test_supplier_id_is_uuid(self, engine):
        supplier = engine.add_supplier("Test", "Germany", "services")
        import uuid
        uuid.UUID(supplier.supplier_id)  # Should not raise

    def test_composite_esg_score_calculation(self, engine):
        supplier = engine.add_supplier(
            "Test", "Germany", "services",
            environmental_score=80, social_score=70, governance_score=60
        )
        # 0.40*80 + 0.35*70 + 0.25*60 = 32 + 24.5 + 15 = 71.5
        assert supplier.esg_scores.composite == pytest.approx(71.5)

    def test_scores_clamped_to_0_100(self, engine):
        supplier = engine.add_supplier(
            "Test", "Germany", "services",
            environmental_score=150, social_score=-10, governance_score=50
        )
        assert supplier.esg_scores.environmental == 100.0
        assert supplier.esg_scores.social == 0.0

    def test_list_suppliers_empty(self, engine):
        assert engine.list_suppliers() == []

    def test_list_suppliers_returns_all(self, engine_with_suppliers):
        suppliers = engine_with_suppliers.list_suppliers()
        assert len(suppliers) == 3

    def test_get_supplier_by_id(self, engine):
        added = engine.add_supplier("Test", "France", "retail")
        retrieved = engine.get_supplier(added.supplier_id)
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_get_nonexistent_supplier(self, engine):
        assert engine.get_supplier("nonexistent-id") is None

    def test_certifications_stored(self, engine):
        supplier = engine.add_supplier(
            "Test", "Germany", "manufacturing",
            certifications=["ISO 14001", "SA8000"]
        )
        assert "ISO 14001" in supplier.certifications
        assert "SA8000" in supplier.certifications

    def test_update_esg_scores(self, engine):
        supplier = engine.add_supplier("Test", "Germany", "services", environmental_score=50)
        updated = engine.update_supplier_esg(supplier.supplier_id, environmental=80)
        assert updated is not None
        assert updated.esg_scores.environmental == 80.0

    def test_update_nonexistent_supplier_returns_none(self, engine):
        result = engine.update_supplier_esg("nonexistent", environmental=80)
        assert result is None


class TestRiskAssessment:
    def test_assess_returns_assessment(self, engine_with_suppliers):
        suppliers = engine_with_suppliers.list_suppliers()
        assessment = engine_with_suppliers.assess_risk(suppliers[0].supplier_id)
        assert assessment is not None

    def test_assess_nonexistent_returns_none(self, engine):
        assert engine.assess_risk("nonexistent-id") is None

    def test_high_esg_low_risk(self, engine):
        """Supplier with high ESG scores, low-risk country/sector should be low risk."""
        supplier = engine.add_supplier(
            "GoodCorp", "Sweden", "software",
            environmental_score=90, social_score=90, governance_score=90,
            data_quality=95,
        )
        assessment = engine.assess_risk(supplier.supplier_id)
        assert assessment is not None
        assert assessment.overall_risk in (RiskLevel.LOW, RiskLevel.MEDIUM)

    def test_low_esg_high_risk_country_gives_high_risk(self, engine):
        """Supplier with low ESG, high-risk country should be high or critical risk."""
        supplier = engine.add_supplier(
            "BadCorp", "Bangladesh", "textile",
            environmental_score=20, social_score=15, governance_score=25,
            data_quality=20,
        )
        assessment = engine.assess_risk(supplier.supplier_id)
        assert assessment is not None
        assert assessment.overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_assessment_has_five_risk_factors(self, engine_with_suppliers):
        suppliers = engine_with_suppliers.list_suppliers()
        assessment = engine_with_suppliers.assess_risk(suppliers[0].supplier_id)
        assert len(assessment.risk_factors) == 5

    def test_risk_factors_have_required_fields(self, engine_with_suppliers):
        suppliers = engine_with_suppliers.list_suppliers()
        assessment = engine_with_suppliers.assess_risk(suppliers[0].supplier_id)
        for rf in assessment.risk_factors:
            assert rf.name
            assert 0 <= rf.score <= 10
            assert rf.weighted_score >= 0

    def test_assessment_has_csrd_references(self, engine_with_suppliers):
        suppliers = engine_with_suppliers.list_suppliers()
        assessment = engine_with_suppliers.assess_risk(suppliers[0].supplier_id)
        assert len(assessment.csrd_article_references) > 0
        assert any("CSRD" in ref for ref in assessment.csrd_article_references)

    def test_assessment_has_recommended_actions(self, engine_with_suppliers):
        suppliers = engine_with_suppliers.list_suppliers()
        for supplier in suppliers:
            assessment = engine_with_suppliers.assess_risk(supplier.supplier_id)
            assert len(assessment.recommended_actions) > 0

    def test_no_certifications_creates_gap(self, engine):
        supplier = engine.add_supplier("NoCerts", "France", "manufacturing", certifications=[])
        assessment = engine.assess_risk(supplier.supplier_id)
        assert any("certif" in gap.lower() for gap in assessment.csrd_compliance_gaps)

    def test_no_audit_creates_gap(self, engine):
        supplier = engine.add_supplier("NoAudit", "France", "manufacturing")
        assessment = engine.assess_risk(supplier.supplier_id)
        assert any("audit" in gap.lower() for gap in assessment.csrd_compliance_gaps)

    def test_assess_all_risks(self, engine_with_suppliers):
        assessments = engine_with_suppliers.assess_all_risks()
        assert len(assessments) == 3

    def test_risk_score_range(self, engine_with_suppliers):
        assessments = engine_with_suppliers.assess_all_risks()
        for a in assessments:
            assert 0 <= a.overall_score <= 100

    def test_tier_2_higher_risk_than_tier_1_same_esg(self, engine):
        s_t1 = engine.add_supplier("T1", "Germany", "services", tier=1,
                                   environmental_score=70, social_score=70, governance_score=70)
        s_t2 = engine.add_supplier("T2", "Germany", "services", tier=2,
                                   environmental_score=70, social_score=70, governance_score=70)
        a_t1 = engine.assess_risk(s_t1.supplier_id)
        a_t2 = engine.assess_risk(s_t2.supplier_id)
        # Higher tier → more risk
        assert a_t2.overall_score > a_t1.overall_score


class TestPortfolioSummary:
    def test_empty_portfolio(self, engine):
        summary = engine.get_portfolio_summary()
        assert summary.total_suppliers == 0
        assert summary.average_esg_score == 0.0

    def test_portfolio_counts(self, engine_with_suppliers):
        summary = engine_with_suppliers.get_portfolio_summary()
        assert summary.total_suppliers == 3
        total_counted = (
            summary.critical_count + summary.high_count
            + summary.medium_count + summary.low_count
        )
        assert total_counted == 3

    def test_total_spend(self, engine_with_suppliers):
        summary = engine_with_suppliers.get_portfolio_summary()
        assert summary.total_annual_spend_eur == pytest.approx(2_000_000)

    def test_csrd_compliance_status_field(self, engine_with_suppliers):
        summary = engine_with_suppliers.get_portfolio_summary()
        assert summary.csrd_compliance_status in ("Compliant", "In Progress", "Non-Compliant")

    def test_top_risks_not_empty(self, engine_with_suppliers):
        summary = engine_with_suppliers.get_portfolio_summary()
        assert len(summary.top_risks) > 0


class TestDueDiligenceChecklist:
    def test_checklist_not_empty(self, engine):
        checklist = engine.get_checklist()
        assert len(checklist) > 0

    def test_checklist_has_required_fields(self, engine):
        for item in engine.get_checklist():
            assert "id" in item
            assert "category" in item
            assert "requirement" in item
            assert "csrd_reference" in item

    def test_checklist_covers_esg_categories(self, engine):
        checklist = engine.get_checklist()
        categories = {item["category"] for item in checklist}
        assert "Environmental" in categories
        assert "Social" in categories
        assert "Governance" in categories

    def test_checklist_has_forced_labour_item(self):
        requirements = [item["requirement"].lower() for item in CSRD_DUE_DILIGENCE_CHECKLIST]
        assert any("forced" in r or "child labour" in r for r in requirements)


class TestCountryAndSectorIndices:
    def test_scandinavia_lower_risk_than_russia(self):
        assert COUNTRY_RISK_INDEX["sweden"] < COUNTRY_RISK_INDEX["russia"]

    def test_bangladesh_high_risk(self):
        assert COUNTRY_RISK_INDEX.get("bangladesh", 5.0) >= 5.0

    def test_software_lower_multiplier_than_mining(self):
        assert SECTOR_RISK_MULTIPLIER["software"] < SECTOR_RISK_MULTIPLIER["mining"]
