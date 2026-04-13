"""Tests for jurisdiction conflict detection."""

from __future__ import annotations

import pytest

from lios.features.jurisdiction_conflict import (
    Conflict,
    JurisdictionConflictDetector,
)


@pytest.fixture
def detector():
    return JurisdictionConflictDetector()


def test_detect_csrd_germany(detector):
    conflicts = detector.detect_conflicts("CSRD", ["Germany"])
    assert len(conflicts) >= 1
    assert all(isinstance(c, Conflict) for c in conflicts)
    regulations = [c.eu_regulation for c in conflicts]
    assert "CSRD" in regulations


def test_detect_sfdr_germany(detector):
    conflicts = detector.detect_conflicts("SFDR", ["Germany"])
    assert len(conflicts) >= 1
    assert all(c.eu_regulation == "SFDR" for c in conflicts)


def test_detect_eu_taxonomy_france(detector):
    conflicts = detector.detect_conflicts("EU_TAXONOMY", ["France"])
    assert len(conflicts) >= 1
    assert all(c.eu_regulation == "EU_TAXONOMY" for c in conflicts)


def test_detect_no_conflicts_for_unknown_jurisdiction(detector):
    conflicts = detector.detect_conflicts("CSRD", ["Atlantis"])
    assert conflicts == []


def test_conflict_has_required_fields(detector):
    conflicts = detector.detect_conflicts("CSRD", ["Germany"])
    for conflict in conflicts:
        assert conflict.eu_regulation
        assert conflict.national_law
        assert conflict.jurisdiction
        assert conflict.conflict_type
        assert conflict.description
        assert conflict.severity in {"high", "medium", "low"}


def test_detect_all_conflicts_germany(detector):
    conflicts = detector.detect_all_conflicts(["Germany"])
    assert len(conflicts) >= 2
    jurs = {c.jurisdiction for c in conflicts}
    assert "Germany" in jurs


def test_detect_all_conflicts_france(detector):
    conflicts = detector.detect_all_conflicts(["France"])
    assert len(conflicts) >= 1
    for c in conflicts:
        assert "France" in c.jurisdiction


def test_get_all_known_conflicts(detector):
    all_conflicts = detector.get_all_known_conflicts()
    assert len(all_conflicts) >= 5
    regs = {c.eu_regulation for c in all_conflicts}
    assert "CSRD" in regs
    assert "SFDR" in regs


def test_case_insensitive_regulation(detector):
    conflicts_upper = detector.detect_conflicts("CSRD", ["Germany"])
    conflicts_lower = detector.detect_conflicts("csrd", ["Germany"])
    assert len(conflicts_upper) == len(conflicts_lower)


def test_multiple_jurisdictions(detector):
    conflicts = detector.detect_all_conflicts(["Germany", "France"])
    jurisdictions = {c.jurisdiction for c in conflicts}
    assert "Germany" in jurisdictions
    assert "France" in jurisdictions


def test_conflict_severity_values(detector):
    all_conflicts = detector.get_all_known_conflicts()
    valid_severities = {"high", "medium", "low"}
    for c in all_conflicts:
        assert c.severity in valid_severities


def test_conflict_type_values(detector):
    all_conflicts = detector.get_all_known_conflicts()
    valid_types = {
        "stricter_national",
        "divergent_definition",
        "format_difference",
        "timeline_difference",
    }
    for c in all_conflicts:
        assert c.conflict_type in valid_types
