"""
Feature 1 – Regulatory Decay Scoring.

Every answer carries a freshness score (0.0 – 1.0) reflecting how current
the underlying regulatory text is.  The score decays linearly from 1.0 on
the day the regulation was last verified, reaching 0.0 at
``settings.decay_threshold_days`` days later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from lios.config import settings
from lios.utils.helpers import utcnow


@dataclass
class DecayResult:
    score: float                      # 0.0 (stale) – 1.0 (fresh)
    days_since_verified: int
    threshold_days: int
    label: str                        # "FRESH" | "AGING" | "STALE"
    warning: Optional[str] = None


class DecayScorer:
    """
    Compute a freshness score for a regulation.

    Parameters
    ----------
    threshold_days:
        Number of days after the last verification date before the score
        reaches zero.  Defaults to ``settings.decay_threshold_days``.
    """

    def __init__(self, threshold_days: Optional[int] = None) -> None:
        self.threshold_days = threshold_days or settings.decay_threshold_days

    def score(self, last_verified_at: Optional[datetime]) -> DecayResult:
        """
        Compute the decay score for a single regulation.

        If *last_verified_at* is ``None`` the score is 0.0 (unknown freshness).
        """
        now = utcnow()

        if last_verified_at is None:
            return DecayResult(
                score=0.0,
                days_since_verified=-1,
                threshold_days=self.threshold_days,
                label="UNKNOWN",
                warning="Verification date not available – treat answer with caution.",
            )

        if last_verified_at.tzinfo is None:
            last_verified_at = last_verified_at.replace(tzinfo=timezone.utc)

        delta = (now - last_verified_at).days
        raw = 1.0 - (delta / self.threshold_days)
        score = max(0.0, min(1.0, raw))

        if score >= 0.8:
            label = "FRESH"
            warning = None
        elif score >= 0.4:
            label = "AGING"
            warning = (
                f"This regulation was last verified {delta} days ago. "
                "Verify against the latest EUR-Lex version before relying on this answer."
            )
        else:
            label = "STALE"
            warning = (
                f"⚠ This regulation was last verified {delta} days ago "
                f"(threshold: {self.threshold_days} days). "
                "The law may have changed significantly."
            )

        return DecayResult(
            score=round(score, 4),
            days_since_verified=delta,
            threshold_days=self.threshold_days,
            label=label,
            warning=warning,
        )

    def aggregate(self, dates: list[Optional[datetime]]) -> DecayResult:
        """Return the minimum (worst) decay score across multiple regulations."""
        results = [self.score(d) for d in dates]
        return min(results, key=lambda r: r.score)
