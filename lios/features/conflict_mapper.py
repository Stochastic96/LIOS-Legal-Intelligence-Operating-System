"""Conflict Mapper – matrix of conflicts across jurisdiction/regulation pairs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lios.features.jurisdiction_conflict import Conflict, JurisdictionConflictDetector


@dataclass
class ConflictMap:
    jurisdictions: list[str]
    regulations: list[str]
    matrix: dict[str, dict[str, list[Conflict]]]  # {jurisdiction: {regulation: [conflicts]}}
    total_conflicts: int
    high_severity_count: int
    summary: str


class ConflictMapper:
    """Build a conflict matrix across multiple jurisdictions and regulations."""

    def __init__(self) -> None:
        self._detector = JurisdictionConflictDetector()

    def map_conflicts(
        self,
        jurisdictions: list[str],
        regulations: list[str],
    ) -> ConflictMap:
        matrix: dict[str, dict[str, list[Conflict]]] = {}
        total = 0
        high_severity = 0

        for jur in jurisdictions:
            matrix[jur] = {}
            for reg in regulations:
                conflicts = self._detector.detect_conflicts(reg, [jur])
                matrix[jur][reg] = conflicts
                total += len(conflicts)
                high_severity += sum(1 for c in conflicts if c.severity == "high")

        summary = self._build_summary(jurisdictions, regulations, total, high_severity)

        return ConflictMap(
            jurisdictions=jurisdictions,
            regulations=regulations,
            matrix=matrix,
            total_conflicts=total,
            high_severity_count=high_severity,
            summary=summary,
        )

    def _build_summary(
        self,
        jurisdictions: list[str],
        regulations: list[str],
        total: int,
        high_severity: int,
    ) -> str:
        if total == 0:
            return (
                f"No conflicts found between {regulations} and national laws in "
                f"{jurisdictions}. EU regulations appear to be implemented consistently "
                f"in these jurisdictions based on available data."
            )
        return (
            f"Found {total} conflict(s) between EU regulations and national laws across "
            f"{len(jurisdictions)} jurisdiction(s). {high_severity} are high severity. "
            f"Review individual conflicts and consult local counsel for affected jurisdictions."
        )
