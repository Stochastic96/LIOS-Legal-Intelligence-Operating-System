"""
Feature 2 – Jurisdiction Conflict Detection.

Detects gaps or contradictions between EU-level law and national implementations.
Ships with a built-in conflict registry; new conflicts can be registered at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConflictRecord:
    """Describes a known or detected jurisdiction conflict."""

    conflict_id: str
    eu_regulation: str       # e.g. "CSRD"
    national_law: str        # e.g. "German HGB §289b"
    jurisdiction: str        # ISO 3166-1 alpha-2, e.g. "DE"
    description: str
    severity: str            # "HIGH" | "MEDIUM" | "LOW"
    source: str = "registry"


# ── Built-in conflict registry ────────────────────────────────────────────────
_BUILTIN_CONFLICTS: list[ConflictRecord] = [
    ConflictRecord(
        conflict_id="CSRD-DE-001",
        eu_regulation="CSRD",
        national_law="German HGB §289b–§289e (CSR-Richtlinie-Umsetzungsgesetz)",
        jurisdiction="DE",
        description=(
            "Germany's current HGB non-financial reporting scope is narrower than CSRD "
            "Art. 19a. Large PIEs with >500 employees are covered under HGB, but CSRD "
            "extends to large companies with >250 employees from FY 2025. "
            "Conflict: transitional gap in German implementation."
        ),
        severity="HIGH",
    ),
    ConflictRecord(
        conflict_id="SFDR-FR-001",
        eu_regulation="SFDR",
        national_law="French Loi Pacte (Article 29 LEC)",
        jurisdiction="FR",
        description=(
            "France's Article 29 LEC imposes additional climate reporting requirements "
            "on asset managers beyond SFDR Level 2 RTS. Conflict: French rules require "
            "scenario analysis not mandated by SFDR Art. 4."
        ),
        severity="MEDIUM",
    ),
    ConflictRecord(
        conflict_id="CSRD-PL-001",
        eu_regulation="CSRD",
        national_law="Polish Accounting Act (Ustawa o rachunkowości)",
        jurisdiction="PL",
        description=(
            "Poland has not yet fully transposed CSRD into national law as of 2024. "
            "Companies relying on Polish accounting law alone may be non-compliant "
            "with CSRD reporting obligations."
        ),
        severity="HIGH",
    ),
]


class JurisdictionConflictDetector:
    """
    Checks for known conflicts between EU regulations and national laws.

    Usage
    -----
    detector = JurisdictionConflictDetector()
    conflicts = detector.detect(query="CSRD", jurisdiction="DE")
    """

    def __init__(self) -> None:
        self._registry: list[ConflictRecord] = list(_BUILTIN_CONFLICTS)

    def register(self, conflict: ConflictRecord) -> None:
        """Add a new conflict record to the registry."""
        self._registry.append(conflict)

    def detect(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
    ) -> list[ConflictRecord]:
        """
        Return conflicts relevant to *query* (and optionally *jurisdiction*).

        Matching is keyword-based against regulation name and description.
        """
        query_upper = query.upper()
        results: list[ConflictRecord] = []

        for record in self._registry:
            # Match if any regulation keyword from the query appears
            if record.eu_regulation.upper() in query_upper or any(
                word in query_upper for word in record.description.upper().split()[:5]
            ):
                if jurisdiction is None or record.jurisdiction.upper() == jurisdiction.upper():
                    results.append(record)

        return sorted(results, key=lambda r: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[r.severity])

    def list_all(self, jurisdiction: Optional[str] = None) -> list[ConflictRecord]:
        if jurisdiction:
            return [r for r in self._registry if r.jurisdiction.upper() == jurisdiction.upper()]
        return list(self._registry)
