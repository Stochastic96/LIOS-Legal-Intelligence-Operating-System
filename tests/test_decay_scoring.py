"""Tests for regulatory decay scoring."""

from __future__ import annotations

import datetime

import pytest

from lios.features.decay_scoring import DecayScore, RegulatoryDecayScorer
from lios.knowledge.regulatory_db import RegulatoryDatabase


@pytest.fixture
def scorer():
    return RegulatoryDecayScorer()


def test_decay_score_returns_dataclass(scorer):
    result = scorer.decay_score("CSRD")
    assert isinstance(result, DecayScore)
    assert result.regulation == "CSRD"


def test_decay_score_range(scorer):
    for reg in ["CSRD", "ESRS", "EU_TAXONOMY", "SFDR"]:
        result = scorer.decay_score(reg)
        assert 0 <= result.score <= 100, f"{reg} score out of range: {result.score}"


def test_decay_score_freshness_labels(scorer):
    valid_labels = {"Current", "Aging", "Stale", "Outdated"}
    for reg in ["CSRD", "ESRS", "EU_TAXONOMY", "SFDR"]:
        result = scorer.decay_score(reg)
        assert result.freshness_label in valid_labels, f"{reg}: unexpected label {result.freshness_label}"


def test_decay_score_unknown_regulation(scorer):
    result = scorer.decay_score("UNKNOWN_REG")
    assert result.score == 0
    assert result.freshness_label == "Unknown"


def test_decay_score_formula():
    """Verify the score formula: 100 - min(100, days/3.65)."""
    scorer = RegulatoryDecayScorer()
    # Use a fixed as_of_date to make test deterministic
    # CSRD last_updated = 2023-01-05
    fixed_date = datetime.date(2024, 1, 5)  # exactly 366 days later
    result = scorer.decay_score("CSRD", as_of_date=fixed_date)
    expected = max(0, min(100, round(100 - 365 / 3.65)))
    assert result.score == expected
    assert result.days_since_update == 365


def test_decay_score_as_of_date(scorer):
    """Older as_of_date should produce lower score (more decay)."""
    early_date = datetime.date(2024, 1, 1)
    late_date = datetime.date(2030, 1, 1)
    early = scorer.decay_score("CSRD", as_of_date=early_date)
    late = scorer.decay_score("CSRD", as_of_date=late_date)
    assert early.score >= late.score


def test_decay_score_all(scorer):
    scores = scorer.score_all()
    assert len(scores) == 4  # CSRD, ESRS, EU_TAXONOMY, SFDR
    regulation_names = [s.regulation for s in scores]
    assert "CSRD" in regulation_names
    assert "SFDR" in regulation_names


def test_decay_label_current():
    scorer = RegulatoryDecayScorer()
    # Score of 90 → "Current"
    assert scorer._label(90) == "Current"
    assert scorer._label(80) == "Current"


def test_decay_label_aging():
    scorer = RegulatoryDecayScorer()
    assert scorer._label(79) == "Aging"
    assert scorer._label(60) == "Aging"


def test_decay_label_stale():
    scorer = RegulatoryDecayScorer()
    assert scorer._label(59) == "Stale"
    assert scorer._label(40) == "Stale"


def test_decay_label_outdated():
    scorer = RegulatoryDecayScorer()
    assert scorer._label(39) == "Outdated"
    assert scorer._label(0) == "Outdated"


def test_decay_days_since_update_positive(scorer):
    result = scorer.decay_score("CSRD")
    assert result.days_since_update >= 0


def test_decay_sfdr_is_older_than_csrd():
    """SFDR (2021) last updated vs CSRD (2023) – SFDR should generally have more decay."""
    scorer = RegulatoryDecayScorer()
    fixed = datetime.date(2025, 1, 1)
    csrd = scorer.decay_score("CSRD", as_of_date=fixed)
    sfdr = scorer.decay_score("SFDR", as_of_date=fixed)
    # SFDR last_updated 2022-01-01 vs CSRD 2023-01-05 → SFDR has more days
    assert sfdr.days_since_update > csrd.days_since_update
    assert sfdr.score <= csrd.score
