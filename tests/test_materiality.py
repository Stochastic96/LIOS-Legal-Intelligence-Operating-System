"""Tests for the Double Materiality Assessment module."""

from __future__ import annotations

import pytest

from lios.features.materiality import (
    DoubleMaterialityEngine,
    MaterialityLevel,
    ESRS_TOPICS,
)


@pytest.fixture
def engine() -> DoubleMaterialityEngine:
    return DoubleMaterialityEngine()


@pytest.fixture
def sample_company_profile() -> dict:
    return {"name": "TestCorp GmbH", "sector": "manufacturing", "employees": 750}


@pytest.fixture
def all_high_inputs() -> list[dict]:
    """All topics rated 5 (very high) on all dimensions."""
    return [
        {
            "esrs_code": code,
            "sub_topic": meta["topic"],
            "impact_severity": 5,
            "impact_scale": 5,
            "impact_likelihood": 5,
            "financial_likelihood": 5,
            "financial_magnitude": 5,
            "financial_time_horizon": "short",
        }
        for code, meta in ESRS_TOPICS.items()
    ]


@pytest.fixture
def all_low_inputs() -> list[dict]:
    """All topics rated 1 (very low) on all dimensions."""
    return [
        {
            "esrs_code": code,
            "sub_topic": meta["topic"],
            "impact_severity": 1,
            "impact_scale": 1,
            "impact_likelihood": 1,
            "financial_likelihood": 1,
            "financial_magnitude": 1,
            "financial_time_horizon": "long",
        }
        for code, meta in ESRS_TOPICS.items()
    ]


class TestESRSTopicCatalog:
    def test_catalog_not_empty(self, engine):
        catalog = engine.get_topic_catalog()
        assert len(catalog) > 0

    def test_all_major_topics_present(self, engine):
        catalog = engine.get_topic_catalog()
        for code in ["E1", "E2", "E3", "E4", "E5", "S1", "S2", "S3", "S4", "G1"]:
            assert code in catalog, f"ESRS topic {code} missing from catalog"

    def test_each_topic_has_required_fields(self, engine):
        catalog = engine.get_topic_catalog()
        for code, meta in catalog.items():
            assert "standard" in meta, f"{code} missing 'standard'"
            assert "topic" in meta, f"{code} missing 'topic'"
            assert "sub_topics" in meta, f"{code} missing 'sub_topics'"

    def test_e1_is_climate_change(self, engine):
        assert engine.get_topic_catalog()["E1"]["topic"] == "Climate Change"

    def test_g1_is_business_conduct(self, engine):
        assert engine.get_topic_catalog()["G1"]["topic"] == "Business Conduct"


class TestMaterialityThresholds:
    def test_high_scores_produce_material_topics(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        material = [t for t in matrix.assessed_topics if t.double_material]
        assert len(material) == len(all_high_inputs), "All high-scored topics should be material"

    def test_low_scores_produce_no_material_topics(
        self, engine, sample_company_profile, all_low_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_low_inputs)
        material = [t for t in matrix.assessed_topics if t.double_material]
        assert len(material) == 0, "All low-scored topics should be not material"

    def test_impact_only_materiality(self, engine, sample_company_profile):
        """A topic with high impact score but low financial score should still be material."""
        inputs = [{
            "esrs_code": "E1",
            "sub_topic": "GHG emissions",
            "impact_severity": 5,
            "impact_scale": 5,
            "impact_likelihood": 5,
            "financial_likelihood": 1,
            "financial_magnitude": 1,
            "financial_time_horizon": "long",
        }]
        matrix = engine.assess(sample_company_profile, inputs)
        e1 = matrix.assessed_topics[0]
        assert e1.impact_material is True
        assert e1.double_material is True

    def test_financial_only_materiality(self, engine, sample_company_profile):
        """A topic with high financial score but low impact score should still be material."""
        inputs = [{
            "esrs_code": "E1",
            "sub_topic": "GHG emissions",
            "impact_severity": 1,
            "impact_scale": 1,
            "impact_likelihood": 1,
            "financial_likelihood": 5,
            "financial_magnitude": 5,
            "financial_time_horizon": "short",
        }]
        matrix = engine.assess(sample_company_profile, inputs)
        e1 = matrix.assessed_topics[0]
        assert e1.financial_material is True
        assert e1.double_material is True


class TestMaterialityScoring:
    def test_impact_score_formula(self, engine, sample_company_profile):
        """Impact score = 0.40*severity + 0.30*scale + 0.30*likelihood."""
        inputs = [{
            "esrs_code": "E1", "sub_topic": "GHG",
            "impact_severity": 4, "impact_scale": 3, "impact_likelihood": 5,
            "financial_likelihood": 1, "financial_magnitude": 1,
            "financial_time_horizon": "long",
        }]
        matrix = engine.assess(sample_company_profile, inputs)
        t = matrix.assessed_topics[0]
        expected = 0.40 * 4 + 0.30 * 3 + 0.30 * 5
        assert t.impact_score == pytest.approx(expected, abs=0.01)

    def test_long_time_horizon_discounts_financial_score(self, engine, sample_company_profile):
        """Long time horizon should produce lower financial score than short."""
        base = {
            "esrs_code": "E1", "sub_topic": "GHG",
            "impact_severity": 2, "impact_scale": 2, "impact_likelihood": 2,
            "financial_likelihood": 4, "financial_magnitude": 4,
        }
        short_input = [{**base, "financial_time_horizon": "short"}]
        long_input = [{**base, "financial_time_horizon": "long"}]

        m_short = engine.assess(sample_company_profile, short_input)
        m_long = engine.assess(sample_company_profile, long_input)

        t_short = m_short.assessed_topics[0]
        t_long = m_long.assessed_topics[0]
        assert t_short.financial_score > t_long.financial_score

    def test_very_high_combined_gives_very_high_level(self, engine, sample_company_profile):
        inputs = [{
            "esrs_code": "E1", "sub_topic": "GHG",
            "impact_severity": 5, "impact_scale": 5, "impact_likelihood": 5,
            "financial_likelihood": 5, "financial_magnitude": 5,
            "financial_time_horizon": "short",
        }]
        matrix = engine.assess(sample_company_profile, inputs)
        assert matrix.assessed_topics[0].materiality_level == MaterialityLevel.VERY_HIGH

    def test_not_material_when_below_threshold(self, engine, sample_company_profile):
        inputs = [{
            "esrs_code": "E1", "sub_topic": "GHG",
            "impact_severity": 1, "impact_scale": 1, "impact_likelihood": 1,
            "financial_likelihood": 1, "financial_magnitude": 1,
            "financial_time_horizon": "long",
        }]
        matrix = engine.assess(sample_company_profile, inputs)
        assert matrix.assessed_topics[0].materiality_level == MaterialityLevel.NOT_MATERIAL

    def test_scores_clamped_to_1_5(self, engine, sample_company_profile):
        """Scores outside 1-5 range should be clamped."""
        inputs = [{
            "esrs_code": "E1", "sub_topic": "GHG",
            "impact_severity": 10,  # Should be clamped to 5
            "impact_scale": -5,     # Should be clamped to 1
            "impact_likelihood": 3,
            "financial_likelihood": 3,
            "financial_magnitude": 3,
            "financial_time_horizon": "medium",
        }]
        matrix = engine.assess(sample_company_profile, inputs)
        t = matrix.assessed_topics[0]
        assert t.impact_severity == 5.0
        assert t.impact_scale == 1.0


class TestMaterialityMatrix:
    def test_matrix_contains_assessed_topics(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        assert len(matrix.assessed_topics) == len(all_high_inputs)

    def test_mandatory_topics_always_present(
        self, engine, sample_company_profile, all_low_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_low_inputs)
        assert "ESRS 1" in matrix.mandatory_topics
        assert "ESRS 2" in matrix.mandatory_topics

    def test_material_topics_codes_match_assessed(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        assessed_codes = {t.esrs_code for t in matrix.assessed_topics if t.double_material}
        assert set(matrix.material_topics) == assessed_codes

    def test_recommended_disclosures_include_esrs2(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        assert any("ESRS 2" in d for d in matrix.recommended_disclosures)

    def test_assessment_summary_not_empty(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        assert len(matrix.assessment_summary) > 0

    def test_next_steps_present(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        assert len(matrix.next_steps) > 0

    def test_csrd_article_references(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        assert len(matrix.csrd_article_references) > 0
        assert any("CSRD" in ref for ref in matrix.csrd_article_references)

    def test_priority_actions_for_material_topics(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        for topic in matrix.assessed_topics:
            if topic.double_material:
                assert len(topic.priority_actions) > 0

    def test_rationale_not_empty(
        self, engine, sample_company_profile, all_high_inputs
    ):
        matrix = engine.assess(sample_company_profile, all_high_inputs)
        for topic in matrix.assessed_topics:
            assert len(topic.rationale) > 0


class TestDefaultAssessmentTemplate:
    def test_manufacturing_template(self, engine):
        inputs = engine.create_default_assessment_inputs(sector="manufacturing")
        assert len(inputs) == len(ESRS_TOPICS)

    def test_finance_template(self, engine):
        inputs = engine.create_default_assessment_inputs(sector="finance")
        assert len(inputs) > 0

    def test_template_has_required_fields(self, engine):
        inputs = engine.create_default_assessment_inputs()
        for inp in inputs:
            assert "esrs_code" in inp
            assert "impact_severity" in inp
            assert "financial_likelihood" in inp
            assert "financial_time_horizon" in inp

    def test_manufacturing_e1_higher_scores(self, engine):
        """Manufacturing sector template should give E1 higher scores than default."""
        mfg_inputs = engine.create_default_assessment_inputs(sector="manufacturing")
        default_inputs = engine.create_default_assessment_inputs(sector="services")
        mfg_e1 = next(i for i in mfg_inputs if i["esrs_code"] == "E1")
        def_e1 = next(i for i in default_inputs if i["esrs_code"] == "E1")
        assert mfg_e1["impact_severity"] >= def_e1["impact_severity"]

    def test_unknown_sector_falls_back_to_defaults(self, engine):
        inputs = engine.create_default_assessment_inputs(sector="unknownsector")
        assert len(inputs) == len(ESRS_TOPICS)
        for inp in inputs:
            assert inp["impact_severity"] == 2
