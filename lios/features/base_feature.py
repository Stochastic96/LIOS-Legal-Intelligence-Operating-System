"""Abstract base class for all LIOS feature modules.

Provides a standard interface so features can be:
- Discovered and loaded dynamically
- Tested in isolation
- Composed inside the orchestration engine consistently
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FeatureResult:
    """Standardised result returned by every feature."""

    feature_type: str
    """Short identifier for the feature (e.g. 'applicability', 'carbon')."""

    data: dict[str, Any]
    """Primary result payload – feature-specific structure."""

    confidence: float = 1.0
    """Confidence in the result (0.0–1.0)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Optional metadata (regulation refs, computation notes, etc.)."""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")


class BaseFeature(ABC):
    """Abstract base for all LIOS analytical feature modules.

    Implementing a feature requires only:
    1. Setting the ``feature_type`` class attribute.
    2. Overriding ``execute()``.

    Example::

        class MyFeature(BaseFeature):
            feature_type = "my_feature"

            def execute(self, query: str, context: dict) -> FeatureResult:
                return FeatureResult(
                    feature_type=self.feature_type,
                    data={"result": "..."},
                )
    """

    feature_type: str = "base"
    """Short unique identifier for this feature."""

    @abstractmethod
    def execute(self, query: str, context: dict[str, Any]) -> FeatureResult:
        """Run the feature and return a standardised result.

        Args:
            query: The user's natural-language query.
            context: Contextual data (e.g. ``company_profile``, ``jurisdictions``).

        Returns:
            FeatureResult with the analysis output.
        """
        ...

    def supports(self, query: str, context: dict[str, Any]) -> bool:
        """Return True if this feature is applicable to the given query/context.

        Override to enable conditional feature activation. By default every
        feature is considered always applicable.

        Args:
            query: The user's query.
            context: Contextual data.

        Returns:
            True if the feature should be executed, False otherwise.
        """
        return True
