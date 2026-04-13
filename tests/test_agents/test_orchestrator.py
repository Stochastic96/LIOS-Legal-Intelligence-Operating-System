"""Tests for decay scoring, applicability checker, and conflict detection."""

from __future__ import annotations

from datetime import timedelta

import pytest

from lios.agents.features.applicability_checker import (
    ApplicabilityChecker,
    CompanyProfile,
    RegulationType,
)
from lios.agents.features.decay_scoring import DecayScorer
from lios.agents.features.jurisdiction_conflict import JurisdictionConflictDetector
from lios.utils.helpers import utcnow


class TestDecayScorer:
    def test_fresh_score(self) -> None:
        scorer = DecayScorer(threshold_days=365)
        result = scorer.score(utcnow() - timedelta(days=10))
        assert result.score > 0.95
        assert result.label == "FRESH"

    def test_aging_score(self) -> None:
        scorer = DecayScorer(threshold_days=365)
        result = scorer.score(utcnow() - timedelta(days=200))
        assert 0.4 <= result.score < 0.8
        assert result.label == "AGING"

    def test_stale_score(self) -> None:
        scorer = DecayScorer(threshold_days=365)
        result = scorer.score(utcnow() - timedelta(days=400))
        assert result.score == 0.0
        assert result.label == "STALE"
        assert result.warning is not None

    def test_unknown_score_when_date_none(self) -> None:
        scorer = DecayScorer()
        result = scorer.score(None)
        assert result.score == 0.0
        assert result.label == "UNKNOWN"


class TestApplicabilityChecker:
    def setup_method(self):
        self.checker = ApplicabilityChecker()

    def _profile(self, **kwargs):
        defaults = dict(
            name="TestCo",
            employees=300,
            turnover_eur=50_000_000,
            balance_sheet_eur=25_000_000,
            is_listed=False,
            is_financial_sector=False,
        )
        defaults.update(kwargs)
        return CompanyProfile(**defaults)

    def test_csrd_applies_to_large_company(self) -> None:
        result = self.checker.check(self._profile(), RegulationType.CSRD)
        assert result.applies is True
        assert result.phase_in_year == 2025

    def test_csrd_does_not_apply_to_small_company(self) -> None:
        result = self.checker.check(
            self._profile(employees=50, turnover_eur=1_000_000, balance_sheet_eur=500_000),
            RegulationType.CSRD,
        )
        assert result.applies is False

    def test_sfdr_applies_to_financial_sector(self) -> None:
        result = self.checker.check(
            self._profile(is_financial_sector=True), RegulationType.SFDR
        )
        assert result.applies is True

    def test_sfdr_does_not_apply_to_non_financial(self) -> None:
        result = self.checker.check(self._profile(), RegulationType.SFDR)
        assert result.applies is False

    def test_csddd_applies_to_tier1(self) -> None:
        result = self.checker.check(
            self._profile(employees=1_500, turnover_eur=500_000_000),
            RegulationType.CSDDD,
        )
        assert result.applies is True
        assert result.phase_in_year == 2027


class TestJurisdictionConflictDetector:
    def setup_method(self):
        self.detector = JurisdictionConflictDetector()

    def test_detects_csrd_germany_conflict(self) -> None:
        conflicts = self.detector.detect("CSRD", jurisdiction="DE")
        assert len(conflicts) >= 1
        assert any(c.conflict_id == "CSRD-DE-001" for c in conflicts)

    def test_filters_by_jurisdiction(self) -> None:
        de_conflicts = self.detector.detect("CSRD", jurisdiction="DE")
        fr_conflicts = self.detector.detect("CSRD", jurisdiction="FR")
        de_ids = {c.conflict_id for c in de_conflicts}
        fr_ids = {c.conflict_id for c in fr_conflicts}
        assert de_ids.isdisjoint(fr_ids) or not de_ids  # DE and FR sets don't share conflicts

    def test_no_conflicts_for_unknown_regulation(self) -> None:
        conflicts = self.detector.detect("UNKNOWN_REGULATION_XYZ")
        assert conflicts == []
