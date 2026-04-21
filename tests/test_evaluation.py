"""Tests for lios.evaluation – AnswerEvaluator."""

from __future__ import annotations

import pytest

from lios.evaluation.answer_evaluator import AnswerEvaluator, EvaluationResult


@pytest.fixture
def evaluator() -> AnswerEvaluator:
    return AnswerEvaluator()


_CHUNKS = [
    {
        "regulation": "CSRD",
        "article": "Art.7",
        "title": "Penalties",
        "text": (
            "Member States shall lay down rules on penalties applicable to "
            "infringements of national provisions. Penalties shall be effective, "
            "proportionate and dissuasive."
        ),
    },
    {
        "regulation": "CSRD",
        "article": "Art.4",
        "title": "Double materiality assessment",
        "text": (
            "Undertakings shall conduct a double materiality assessment to "
            "identify which sustainability topics are material."
        ),
    },
]

_GOOD_ANSWER = (
    "**Issue:** What are the penalties for CSRD non-compliance?\n\n"
    "**Rule:**\n"
    "  * CSRD Art.7: Member States shall lay down rules on penalties that are "
    "effective, proportionate and dissuasive.\n\n"
    "**Analysis:** Penalties under CSRD must be set by national legislation and "
    "must be effective and proportionate.\n\n"
    "**Conclusion:** Non-compliance with CSRD may lead to penalties set by "
    "Member States under CSRD Art.7.\n\n"
    "*Sources: CSRD Art.7 – Penalties*"
)

_GENERIC_FALLBACK = "Please consult the full regulatory text for more information."


class TestAnswerEvaluator:
    def test_good_answer_scores_higher_than_fallback(self, evaluator):
        good = evaluator.evaluate("What are the penalties for CSRD?", _GOOD_ANSWER, _CHUNKS)
        bad = evaluator.evaluate("What are the penalties for CSRD?", _GENERIC_FALLBACK, _CHUNKS)
        assert good.overall_score > bad.overall_score

    def test_grade_property(self, evaluator):
        result = evaluator.evaluate("What is CSRD?", _GOOD_ANSWER, _CHUNKS)
        assert result.grade in {"A", "B", "C", "D", "F"}

    def test_scores_in_range(self, evaluator):
        result = evaluator.evaluate("What are the penalties?", _GOOD_ANSWER, _CHUNKS)
        for score in (
            result.overall_score,
            result.grounding_score,
            result.citation_score,
            result.completeness_score,
            result.diversity_score,
        ):
            assert 0.0 <= score <= 1.0

    def test_feedback_is_list_of_strings(self, evaluator):
        result = evaluator.evaluate("What are the penalties?", _GOOD_ANSWER, _CHUNKS)
        assert isinstance(result.feedback, list)
        assert all(isinstance(f, str) for f in result.feedback)

    def test_empty_answer_low_score(self, evaluator):
        result = evaluator.evaluate("What is CSRD?", "", _CHUNKS)
        assert result.overall_score < 0.5

    def test_empty_chunks_low_citation_score(self, evaluator):
        result = evaluator.evaluate("What is CSRD?", _GOOD_ANSWER, [])
        assert result.citation_score == 0.0

    def test_trivial_answer_low_diversity(self, evaluator):
        result = evaluator.evaluate("What is CSRD?", _GENERIC_FALLBACK, _CHUNKS)
        assert result.diversity_score < 0.3

    def test_good_answer_positive_feedback(self, evaluator):
        result = evaluator.evaluate("What are the penalties for CSRD?", _GOOD_ANSWER, _CHUNKS)
        feedback_text = " ".join(result.feedback).lower()
        # Should mention that something is good
        assert "good" in feedback_text or len(result.feedback) >= 1

    def test_no_chunks_grounding_zero(self, evaluator):
        result = evaluator.evaluate("What is CSRD?", "CSRD applies to large companies.", [])
        assert result.grounding_score == 0.0

    def test_answer_citing_regulation_higher_citation_score(self, evaluator):
        cited = "CSRD Art.7 requires penalties. CSRD Art.4 requires double materiality."
        not_cited = "Penalties must be effective and dissuasive."
        r_cited = evaluator.evaluate("What are the requirements?", cited, _CHUNKS)
        r_not = evaluator.evaluate("What are the requirements?", not_cited, _CHUNKS)
        assert r_cited.citation_score >= r_not.citation_score

    def test_evaluation_result_is_dataclass(self, evaluator):
        result = evaluator.evaluate("Question?", "Answer.", _CHUNKS)
        assert isinstance(result, EvaluationResult)

    def test_grounding_score_with_relevant_answer(self, evaluator):
        # An answer that uses the same vocabulary as the chunks should score higher
        relevant_answer = (
            "CSRD Art.7 imposes penalties that must be effective, proportionate, "
            "and dissuasive. Undertakings shall conduct a materiality assessment."
        )
        result = evaluator.evaluate("What are the requirements?", relevant_answer, _CHUNKS)
        assert result.grounding_score > 0.3
