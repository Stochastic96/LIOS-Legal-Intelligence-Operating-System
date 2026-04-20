"""Answer grounding validator.

Checks whether a generated answer is substantiated by the retrieved context
rather than hallucinated.  Uses a lightweight keyword-overlap heuristic that
works without an external LLM.

Cross-language handling
-----------------------
The LIOS system retrieves German legal text and answers in English.
A purely ASCII tokenizer would drop all German tokens (umlauts, etc.),
making it impossible to establish overlap between a German context and an
English answer.  This validator:

1. Uses a Unicode-aware tokenizer that preserves umlauts and other
   non-ASCII letters so German context tokens are counted correctly.
2. Returns ``"UNKNOWN"`` (rather than ``"INVALID"``) when the context
   appears to be in a different language from the answer, so that
   callers can distinguish "cannot verify" from "definitely wrong".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Outcome of a grounding check.

    Attributes:
        status:   ``"VALID"`` when grounded, ``"INVALID"`` when likely
                  hallucinated, or ``"UNKNOWN"`` when cross-language
                  overlap cannot be reliably measured.
        score:    Grounding score in [0, 1] (overlap ratio).
        reason:   Human-readable explanation.
    """

    status: str   # "VALID" | "INVALID" | "UNKNOWN"
    score: float
    reason: str

    @property
    def is_valid(self) -> bool:
        return self.status == "VALID"


_MIN_GROUNDING_SCORE = 0.15  # at least 15 % of answer tokens present in context

# Minimum proportion of non-ASCII characters that marks a text as
# "likely non-English" (i.e., possibly German).
# German legal text typically has ~1-3% umlaut/eszett characters, so 1% is a
# reliable lower bound that avoids false positives on English text.
_NON_ASCII_THRESHOLD = 0.01


def _tokenize(text: str) -> set[str]:
    """Return lower-cased Unicode word tokens of length >= 3.

    Uses Unicode category matching so that characters like a-umlaut (ae),
    o-umlaut (oe), and eszett (ss) are preserved and counted correctly.
    """
    # Match runs of Unicode letters/digits (category L* and N*)
    tokens = re.findall(r"[\w]{3,}", text.lower(), flags=re.UNICODE)
    return set(tokens)


def _is_likely_non_english(text: str) -> bool:
    """Heuristic: returns True when *text* contains many non-ASCII characters."""
    if not text:
        return False
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    return (non_ascii / max(1, len(text))) >= _NON_ASCII_THRESHOLD


def validate(answer: str, context: str) -> ValidationResult:
    """Check whether *answer* is grounded in *context*.

    The validator computes the fraction of content words in the answer that
    also appear in the context.  Answers that exceed ``_MIN_GROUNDING_SCORE``
    are labelled ``"VALID"``; those below the threshold are ``"INVALID"``.

    When the context appears to be in a different language from the answer
    (e.g., German context with an English answer, as is typical in LIOS),
    the result is ``"UNKNOWN"`` rather than ``"INVALID"`` because
    cross-language overlap cannot be reliably measured without translation.

    Short or empty answers that explicitly decline to answer (e.g. contain the
    phrase "does not contain" or "don't know") are automatically ``"VALID"``
    because they are the correct response to an unanswerable question.

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

    answer_lower = answer.lower()
    # Answers that explicitly disclaim knowledge are correctly grounded.
    if (
        "does not contain" in answer_lower
        or "no relevant context" in answer_lower
        or "don't know" in answer_lower
        or "i don't know" in answer_lower
    ):
        return ValidationResult(
            status="VALID",
            score=1.0,
            reason="Answer correctly declines due to insufficient context.",
        )

    answer_tokens = _tokenize(answer)
    context_tokens = _tokenize(context)

    if not answer_tokens:
        return ValidationResult(
            status="INVALID",
            score=0.0,
            reason="Answer contains no recognizable tokens.",
        )

    # Cross-language detection: if context has many non-ASCII chars and the
    # answer is mostly ASCII (English), overlap measurement is unreliable.
    if _is_likely_non_english(context) and not _is_likely_non_english(answer):
        overlap = answer_tokens & context_tokens
        score = len(overlap) / len(answer_tokens)
        return ValidationResult(
            status="UNKNOWN",
            score=round(score, 4),
            reason=(
                "Context appears to be in a different language from the answer. "
                "Cross-language overlap cannot be reliably measured. "
                f"Raw overlap: {len(overlap)}/{len(answer_tokens)} tokens ({score:.0%})."
            ),
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
            f"({score:.0%}) found in context -- answer may be hallucinated."
        ),
    )
