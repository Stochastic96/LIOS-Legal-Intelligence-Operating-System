"""Answer quality evaluation for LIOS.

:class:`AnswerEvaluator` scores a generated answer along four dimensions:

* **Grounding** – Does the answer reference terms/concepts from the source chunks?
* **Citation completeness** – Are the relevant regulations cited?
* **Completeness** – Does the answer address the key aspects of the question?
* **Response diversity** – Is the answer substantively different from a trivial fallback?

These scores combine into an overall quality score (0.0–1.0) and actionable
feedback messages.

Usage::

    from lios.evaluation.answer_evaluator import AnswerEvaluator

    evaluator = AnswerEvaluator()
    result = evaluator.evaluate(
        question="What are the penalties for CSRD non-compliance?",
        answer="Based on CSRD Art.7…",
        chunks=[{"regulation": "CSRD", "article": "Art.7", "text": "…"}],
    )
    print(result.overall_score)   # e.g. 0.82
    print(result.feedback)        # ["Citation coverage is good.", ...]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class EvaluationResult:
    """Quality assessment for a single generated answer.

    Attributes:
        overall_score:       Weighted aggregate of the four sub-scores (0–1).
        grounding_score:     How well the answer is grounded in source chunks (0–1).
        citation_score:      Fraction of source regulations explicitly cited (0–1).
        completeness_score:  How thoroughly the answer addresses the question (0–1).
        diversity_score:     How different the answer is from a trivial template (0–1).
        feedback:            Human-readable improvement suggestions.
    """

    overall_score: float
    grounding_score: float
    citation_score: float
    completeness_score: float
    diversity_score: float
    feedback: list[str] = field(default_factory=list)

    @property
    def grade(self) -> str:
        """Letter grade: A (≥0.85), B (≥0.70), C (≥0.55), D (≥0.40), F (<0.40)."""
        if self.overall_score >= 0.85:
            return "A"
        if self.overall_score >= 0.70:
            return "B"
        if self.overall_score >= 0.55:
            return "C"
        if self.overall_score >= 0.40:
            return "D"
        return "F"


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class AnswerEvaluator:
    """Evaluate the quality of a generated legal answer.

    All scoring uses lightweight heuristics (no LLM required).  Scores are
    intentionally conservative – a perfect score is hard to achieve without a
    complete, well-cited, and nuanced answer.

    Weights for the overall score:
    * Grounding:      40 %
    * Citation:       30 %
    * Completeness:   20 %
    * Diversity:      10 %
    """

    _W_GROUNDING = 0.40
    _W_CITATION = 0.30
    _W_COMPLETENESS = 0.20
    _W_DIVERSITY = 0.10

    # Minimum significant token length
    _MIN_LEN = 4

    # Phrases that indicate a trivial / fallback answer
    _TRIVIAL_PHRASES = [
        "please consult the full regulatory text",
        "insufficient regulatory data",
        "no relevant legal context",
        "agent analysis temporarily unavailable",
        "consult the applicable regulation",
    ]

    # Question keywords that signal which topics should appear in the answer
    _TOPIC_KEYWORDS: dict[str, list[str]] = {
        "penalty": ["penalty", "penalt", "fine", "sanction", "enforcement"],
        "applicability": ["applies", "applicable", "subject to", "threshold", "exempt"],
        "requirement": ["shall", "must", "required", "obligation", "disclose"],
        "timeline": ["2024", "2025", "2026", "2027", "2028", "deadline", "financial year"],
        "definition": ["means", "defined as", "definition", "refers to"],
    }

    def evaluate(
        self,
        question: str,
        answer: str,
        chunks: list[dict[str, Any]],
    ) -> EvaluationResult:
        """Evaluate *answer* quality given *question* and source *chunks*.

        Args:
            question: The original user question.
            answer:   The generated answer to evaluate.
            chunks:   Source chunks used to generate the answer.

        Returns:
            An :class:`EvaluationResult` with scores and feedback.
        """
        grounding = self._score_grounding(answer, chunks)
        citation = self._score_citations(answer, chunks)
        completeness = self._score_completeness(question, answer)
        diversity = self._score_diversity(answer)

        overall = (
            grounding * self._W_GROUNDING
            + citation * self._W_CITATION
            + completeness * self._W_COMPLETENESS
            + diversity * self._W_DIVERSITY
        )
        overall = round(min(1.0, max(0.0, overall)), 3)

        feedback = self._generate_feedback(grounding, citation, completeness, diversity, chunks)

        return EvaluationResult(
            overall_score=overall,
            grounding_score=round(grounding, 3),
            citation_score=round(citation, 3),
            completeness_score=round(completeness, 3),
            diversity_score=round(diversity, 3),
            feedback=feedback,
        )

    # ------------------------------------------------------------------
    # Grounding score
    # ------------------------------------------------------------------

    def _score_grounding(self, answer: str, chunks: list[dict[str, Any]]) -> float:
        """Score how much of the answer content is rooted in the source chunks."""
        if not chunks or not answer.strip():
            return 0.0

        answer_tokens = self._tokenize(answer)
        if not answer_tokens:
            return 0.0

        chunk_tokens: set[str] = set()
        for c in chunks:
            chunk_tokens |= self._tokenize(
                f"{c.get('regulation', '')} {c.get('article', '')} "
                f"{c.get('title', '')} {c.get('text', '')}"
            )

        overlap = answer_tokens & chunk_tokens
        # Score is overlap fraction, capped at 1.0
        score = len(overlap) / max(1, len(answer_tokens))
        # Apply a moderate boost for answers referencing regulation names
        reg_names = {c.get("regulation", "").lower() for c in chunks if c.get("regulation")}
        answer_lower = answer.lower()
        if any(r in answer_lower for r in reg_names if r):
            score = min(1.0, score * 1.3)
        return min(1.0, score)

    # ------------------------------------------------------------------
    # Citation score
    # ------------------------------------------------------------------

    def _score_citations(self, answer: str, chunks: list[dict[str, Any]]) -> float:
        """Score how many source regulations are explicitly cited in the answer."""
        if not chunks:
            return 0.0

        # Collect unique regulation/article identifiers from chunks
        identifiers: set[str] = set()
        for c in chunks:
            reg = (c.get("regulation") or "").strip().upper()
            article = (c.get("article") or "").strip().upper()
            if reg:
                identifiers.add(reg)
            if article:
                identifiers.add(article.upper())

        if not identifiers:
            return 0.0

        answer_upper = answer.upper()
        cited = sum(1 for ident in identifiers if ident in answer_upper)
        score = cited / len(identifiers)
        return min(1.0, score)

    # ------------------------------------------------------------------
    # Completeness score
    # ------------------------------------------------------------------

    def _score_completeness(self, question: str, answer: str) -> float:
        """Score how thoroughly the answer addresses the question's intent."""
        if not answer.strip():
            return 0.0

        question_lower = question.lower()
        answer_lower = answer.lower()

        # Check which topic categories are relevant to the question
        relevant_topics = [
            topic
            for topic, kws in self._TOPIC_KEYWORDS.items()
            if any(kw in question_lower for kw in kws)
        ]

        if not relevant_topics:
            # Generic completeness: penalise very short answers
            word_count = len(answer.split())
            return min(1.0, word_count / 80)

        # For each relevant topic, check whether the answer contains related terms
        addressed = 0
        for topic in relevant_topics:
            topic_kws = self._TOPIC_KEYWORDS[topic]
            if any(kw in answer_lower for kw in topic_kws):
                addressed += 1

        base_score = addressed / len(relevant_topics)

        # Length penalty: very short answers score lower
        word_count = len(answer.split())
        length_factor = min(1.0, word_count / 60)

        return min(1.0, base_score * 0.7 + length_factor * 0.3)

    # ------------------------------------------------------------------
    # Diversity score
    # ------------------------------------------------------------------

    def _score_diversity(self, answer: str) -> float:
        """Score how far the answer is from a trivial / fallback template."""
        if not answer.strip():
            return 0.0

        answer_lower = answer.lower()

        # Check for trivial fallback phrases
        for phrase in self._TRIVIAL_PHRASES:
            if phrase in answer_lower:
                return 0.1

        # Use answer length and structural richness as diversity proxies
        word_count = len(answer.split())
        has_structure = bool(re.search(r"\*\*\w+", answer))  # bold headers
        has_bullets = bool(re.search(r"^\s*[•\-\*]", answer, re.MULTILINE))
        has_citations = bool(re.search(r"\b(art\.|article|regulation)\b", answer_lower))

        score = 0.0
        score += min(0.5, word_count / 200)
        if has_structure:
            score += 0.2
        if has_bullets:
            score += 0.15
        if has_citations:
            score += 0.15

        return min(1.0, score)

    # ------------------------------------------------------------------
    # Feedback generation
    # ------------------------------------------------------------------

    def _generate_feedback(
        self,
        grounding: float,
        citation: float,
        completeness: float,
        diversity: float,
        chunks: list[dict[str, Any]],
    ) -> list[str]:
        feedback: list[str] = []

        if grounding < 0.30:
            feedback.append(
                "Grounding is low: the answer contains few terms from the source "
                "chunks.  Ensure the answer draws directly on the retrieved legal text."
            )
        elif grounding >= 0.60:
            feedback.append("Grounding is good: answer content is well-rooted in source material.")

        if citation < 0.30:
            missing = {
                f"{c.get('regulation', '')} {c.get('article', '')}".strip()
                for c in chunks[:3]
                if c.get("regulation")
            }
            if missing:
                feedback.append(
                    f"Citation coverage is low.  Consider explicitly citing: "
                    + ", ".join(sorted(missing))
                )
        elif citation >= 0.60:
            feedback.append("Citation coverage is good.")

        if completeness < 0.40:
            feedback.append(
                "Completeness is low: the answer may not address all key aspects of "
                "the question.  Add more detail on the specific topic asked about."
            )

        if diversity < 0.25:
            feedback.append(
                "Answer appears to be a generic fallback.  Provide a specific, "
                "structured response using the retrieved legal context."
            )

        if not feedback:
            feedback.append("Answer quality looks good overall.")

        return feedback

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> set[str]:
        return {
            tok.lower()
            for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9]{3,}", text)
        }
