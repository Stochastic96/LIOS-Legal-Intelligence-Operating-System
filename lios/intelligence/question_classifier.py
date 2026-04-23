"""Question type classifier for LIOS legal queries.

Classifies incoming user questions into semantic categories so that
:class:`~lios.intelligence.answer_synthesizer.AnswerSynthesizer` can apply
the most appropriate answer-construction strategy.
"""

from __future__ import annotations

import re
from enum import Enum


class QuestionType(str, Enum):
    """Semantic category of a user's legal question."""

    DEFINITION = "definition"
    """'What is X?' / 'Define X' / 'What does X mean?'"""

    APPLICABILITY = "applicability"
    """'Does X apply to Y?' / 'Who must comply?' / 'Are we subject to X?'"""

    REQUIREMENT = "requirement"
    """'What are the requirements?' / 'What must we disclose?' / 'What obligations?'"""

    PROCEDURE = "procedure"
    """'How do I comply?' / 'What steps?' / 'How to implement?'"""

    TIMELINE = "timeline"
    """'When does X apply?' / 'What is the deadline?' / 'By when?'"""

    COMPARISON = "comparison"
    """'What is the difference between X and Y?' / 'X vs Y?'"""

    PENALTY = "penalty"
    """'What are the penalties?' / 'What happens if we don't comply?' / 'Fines?'"""

    GENERAL = "general"
    """Catch-all for questions not matching other patterns."""


# ---------------------------------------------------------------------------
# Compiled regex patterns – built once at module import time.
# ORDER MATTERS: first match wins; place more specific patterns before broad ones.
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[QuestionType, re.Pattern[str]]] = [
    (
        QuestionType.PENALTY,
        re.compile(
            r"\b(penalt|fine[s]?|sanction|enforcement|consequence[s]?\s+of|"
            r"what\s+happens\s+if|non.compliance|fail\s+to\s+comply|"
            r"breach|violation|infringement)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QuestionType.COMPARISON,
        re.compile(
            r"\b(difference\s+between|compare|versus|vs\.?|compared\s+to|"
            r"distinction\s+between|how\s+does\s+\w+\s+differ|"
            r"what\s+distinguishes)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QuestionType.TIMELINE,
        re.compile(
            r"\b(when\s+(does|must|shall|will|is)|by\s+when|deadline|"
            r"timeline|phased|implementation\s+date|by\s+\d{4}|"
            r"from\s+(fy|financial\s+year|january|2024|2025|2026|2027|2028)|"
            r"(first|next)\s+reporting\s+(year|period))\b",
            re.IGNORECASE,
        ),
    ),
    (
        QuestionType.PROCEDURE,
        re.compile(
            r"\b(how\s+(do|can|should|to)\s+(i|we|a\s+company)|"
            r"what\s+(steps|process|procedure|approach)|"
            r"how\s+(to\s+)?(comply|implement|achieve|prepare|conduct)|"
            r"step[s]?\s+(to|for|in)|guide\s+(to|for))\b",
            re.IGNORECASE,
        ),
    ),
    (
        QuestionType.REQUIREMENT,
        re.compile(
            r"\b(what\s+(are|were)\s+the\s+(requirement|obligation|disclosure|rule|standard)|"
            r"what\s+(must|shall|should)\s+\w+\s+(disclose|report|include|do)|"
            r"what\s+information\s+(must|shall|is\s+required)|"
            r"required\s+to\s+(disclose|report|include)|"
            r"disclosure\s+requirement|reporting\s+obligation)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QuestionType.APPLICABILITY,
        re.compile(
            r"\b(does\s+\w+\s+apply|who\s+(must|shall|has\s+to)|"
            r"which\s+compan|are\s+we\s+subject|do\s+we\s+(need|have\s+to)|"
            r"is\s+\w+\s+(applicable|required\s+for|mandatory\s+for)|"
            r"applies\s+to|applicable\s+to|subject\s+to)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QuestionType.DEFINITION,
        re.compile(
            r"\b(what\s+is|what\s+are|define|definition\s+of|meaning\s+of|"
            r"what\s+does\s+\w+\s+mean|explain)\b",
            re.IGNORECASE,
        ),
    ),
]


class QuestionClassifier:
    """Classify a user question into a :class:`QuestionType`.

    Uses ordered regex pattern matching; the first match wins.  Falls back to
    :attr:`QuestionType.GENERAL` when nothing matches.

    Examples::

        classifier = QuestionClassifier()
        qt = classifier.classify("What is double materiality?")
        # → QuestionType.DEFINITION

        qt = classifier.classify("When does CSRD apply to listed SMEs?")
        # → QuestionType.TIMELINE
    """

    def classify(self, question: str) -> QuestionType:
        """Return the most likely :class:`QuestionType` for *question*."""
        for qtype, pattern in _PATTERNS:
            if pattern.search(question):
                return qtype
        return QuestionType.GENERAL

    def classify_all(self, question: str) -> list[QuestionType]:
        """Return all matching question types (ordered by priority)."""
        matches: list[QuestionType] = []
        for qtype, pattern in _PATTERNS:
            if pattern.search(question):
                matches.append(qtype)
        return matches or [QuestionType.GENERAL]


# ---------------------------------------------------------------------------
# Easy-question routing helper
# ---------------------------------------------------------------------------

_COMPANY_CONTEXT_RE = re.compile(
    r"\b(\d[\d,\.]*\s*(employees?|staff|workers?|fte|turnover|revenue|sales)|"
    r"our\s+company|we\s+have|we\s+are|our\s+business|my\s+company)\b",
    re.IGNORECASE,
)
_ARTICLE_REF_RE = re.compile(
    r"\b(art(?:icle)?\.?\s*\d+\w*|§\s*\d+\w*|paragraph\s+\d+\w*|recital\s+\d+\w*|annex\s+[ivxIVX]+\w*)",
    re.IGNORECASE,
)


def is_easy_question(question: str, qtype: QuestionType) -> bool:
    """Return True when the LLM can answer directly without corpus retrieval.

    A question is considered easy when all of the following hold:
    - The type is DEFINITION or GENERAL (not applicability, penalty, etc.)
    - The question contains no company-specific metrics (employee counts, turnover)
    - The question does not reference a specific article, paragraph, or annex number
    """
    if qtype not in (QuestionType.DEFINITION, QuestionType.GENERAL):
        return False
    if _COMPANY_CONTEXT_RE.search(question):
        return False
    if _ARTICLE_REF_RE.search(question):
        return False
    return True
