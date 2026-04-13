"""Regulatory Decay Scoring – measures how fresh a regulation is."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from lios.knowledge.regulatory_db import RegulatoryDatabase


@dataclass
class DecayScore:
    regulation: str
    score: int           # 0-100 (100 = freshest)
    last_updated: str
    days_since_update: int
    freshness_label: str  # "Current" | "Aging" | "Stale" | "Outdated"
    as_of_date: str


class RegulatoryDecayScorer:
    """Compute freshness scores for regulations based on their last update date."""

    LABEL_THRESHOLDS = [
        (80, "Current"),
        (60, "Aging"),
        (40, "Stale"),
        (0, "Outdated"),
    ]

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        self.db = db or RegulatoryDatabase()

    def decay_score(
        self,
        regulation_name: str,
        as_of_date: datetime.date | None = None,
    ) -> DecayScore:
        """Return a DecayScore for the given regulation."""
        if as_of_date is None:
            as_of_date = datetime.date.today()

        reg = self.db.get_regulation(regulation_name)
        if reg is None:
            return DecayScore(
                regulation=regulation_name,
                score=0,
                last_updated="unknown",
                days_since_update=-1,
                freshness_label="Unknown",
                as_of_date=as_of_date.isoformat(),
            )

        last_updated_str = reg.get("last_updated", "")
        try:
            last_updated_date = datetime.date.fromisoformat(last_updated_str)
        except ValueError:
            last_updated_date = datetime.date(2000, 1, 1)

        days_since = (as_of_date - last_updated_date).days
        score = max(0, min(100, round(100 - days_since / 3.65)))
        label = self._label(score)

        return DecayScore(
            regulation=regulation_name,
            score=score,
            last_updated=last_updated_str,
            days_since_update=days_since,
            freshness_label=label,
            as_of_date=as_of_date.isoformat(),
        )

    def score_all(self, as_of_date: datetime.date | None = None) -> list[DecayScore]:
        """Return decay scores for all known regulations."""
        regs = self.db.get_all_regulations()
        return [self.decay_score(r["key"], as_of_date) for r in regs]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _label(self, score: int) -> str:
        for threshold, label in self.LABEL_THRESHOLDS:
            if score >= threshold:
                return label
        return "Outdated"
