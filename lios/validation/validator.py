"""Answer grounding validator.

Checks whether a generated answer is substantiated by the retrieved context
rather than hallucinated.  Uses a lightweight keyword-overlap heuristic that
works without an external LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Outcome of a grounding check.

    Attributes:
        status:   ``"VALID"`` when the answer is grounded; ``"INVALID"`` otherwise.
        score:    Grounding score in [0, 1] (overlap ratio).
        reason:   Human-readable explanation.
    """

    status: str       # "VALID" | "INVALID"
    score: float
    reason: str

    @property
    def is_valid(self) -> bool:
        return self.status == "VALID"


_MIN_GROUNDING_SCORE = 0.15  # at least 15 % of answer tokens present in context


def _tokenize(text: str) -> set[str]:
    """Return lower-cased alpha-numeric tokens of length ≥ 3."""
    return {w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", text.lower())}


def validate(answer: str, context: str) -> ValidationResult:
    """Check whether *answer* is grounded in *context*.

    The validator computes the fraction of content words in the answer that
    also appear in the context.  Answers that exceed :data:`_MIN_GROUNDING_SCORE`
    are labelled ``"VALID"``; those below the threshold are ``"INVALID"``.

    Short or empty answers that explicitly decline to answer (e.g. contain the
    phrase "does not contain") are automatically considered ``"VALID"`` because
    they are the correct response to an unanswerable question.

    Args:
        answer:  The LLM-generated response text.
        context: The retrieved legal context fed to the LLM.

    Returns:
        A :class:`ValidationResult` instance.
    """
    if not answer.strip():
        return ValidationResult(
            status="INVALID",
            score=0.0,
            reason="Empty answer.",
        )

    # Answers that explicitly disclaim knowledge are correctly grounded.
    if "does not contain" in answer.lower() or "no relevant context" in answer.lower():
        return ValidationResult(
            status="VALID",
            score=1.0,
            reason="Answer correctly declines to answer due to insufficient context.",
        )

    answer_tokens = _tokenize(answer)
    context_tokens = _tokenize(context)

    if not answer_tokens:
        return ValidationResult(
            status="INVALID",
            score=0.0,
            reason="Answer contains no recognizable tokens.",
        )

    overlap = answer_tokens & context_tokens
    score = len(overlap) / len(answer_tokens)

    if score >= _MIN_GROUNDING_SCORE:
        return ValidationResult(
            status="VALID",
            score=round(score, 4),
            reason=(
                f"{len(overlap)}/{len(answer_tokens)} answer tokens "
                f"({score:.0%}) found in context."
            ),
        )

    return ValidationResult(
        status="INVALID",
        score=round(score, 4),
        reason=(
            f"Only {len(overlap)}/{len(answer_tokens)} answer tokens "
            f"({score:.0%}) found in context – answer may be hallucinated."
        ),
    )
