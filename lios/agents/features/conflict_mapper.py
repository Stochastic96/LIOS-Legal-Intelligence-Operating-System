"""
Feature 6 – Cross-Jurisdiction Conflict Mapper.

Generates a structured conflict map for attorneys and ESG consultants,
showing where EU law and national law diverge for a given set of regulations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from lios.agents.features.jurisdiction_conflict import (
    ConflictRecord,
    JurisdictionConflictDetector,
)


@dataclass
class ConflictMapEntry:
    eu_regulation: str
    national_law: str
    jurisdiction: str
    severity: str
    description: str
    conflict_id: str


@dataclass
class ConflictMap:
    query: str
    jurisdictions_checked: list[str]
    entries: list[ConflictMapEntry] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.entries)

    @property
    def high_severity_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == "HIGH")

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "jurisdictions_checked": self.jurisdictions_checked,
            "conflict_count": len(self.entries),
            "high_severity_count": self.high_severity_count,
            "conflicts": [
                {
                    "conflict_id": e.conflict_id,
                    "eu_regulation": e.eu_regulation,
                    "national_law": e.national_law,
                    "jurisdiction": e.jurisdiction,
                    "severity": e.severity,
                    "description": e.description,
                }
                for e in self.entries
            ],
        }


class ConflictMapper:
    """
    Build a cross-jurisdiction conflict map for a given query.

    Parameters
    ----------
    jurisdictions:
        List of ISO 3166-1 alpha-2 country codes to check.
        Pass ``None`` to check all jurisdictions in the registry.
    """

    def __init__(
        self,
        detector: Optional[JurisdictionConflictDetector] = None,
        jurisdictions: Optional[list[str]] = None,
    ) -> None:
        self._detector = detector or JurisdictionConflictDetector()
        self._jurisdictions = jurisdictions

    def map(self, query: str) -> ConflictMap:
        """Return a ``ConflictMap`` for *query* across all configured jurisdictions."""
        if self._jurisdictions:
            records: list[ConflictRecord] = []
            for jur in self._jurisdictions:
                records.extend(self._detector.detect(query, jurisdiction=jur))
        else:
            records = self._detector.detect(query)

        entries = [
            ConflictMapEntry(
                eu_regulation=r.eu_regulation,
                national_law=r.national_law,
                jurisdiction=r.jurisdiction,
                severity=r.severity,
                description=r.description,
                conflict_id=r.conflict_id,
            )
            for r in records
        ]

        jurs_checked = self._jurisdictions or list({r.jurisdiction for r in records})
        return ConflictMap(query=query, jurisdictions_checked=jurs_checked, entries=entries)
