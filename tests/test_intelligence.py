"""Tests for lios.intelligence – QuestionClassifier, AnswerSynthesizer, FactVerifier."""

from __future__ import annotations

import pytest

from lios.intelligence.answer_synthesizer import AnswerSynthesizer
from lios.intelligence.fact_verifier import FactVerifier
from lios.intelligence.question_classifier import QuestionClassifier, QuestionType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier() -> QuestionClassifier:
    return QuestionClassifier()


@pytest.fixture
def synthesizer() -> AnswerSynthesizer:
    return AnswerSynthesizer()


@pytest.fixture
def verifier() -> FactVerifier:
    return FactVerifier()


_CSRD_ART7_CHUNK = {
    "regulation": "CSRD",
    "article": "Art.7",
    "title": "Penalties",
    "text": (
        "Member States shall lay down rules on penalties applicable to infringements "
        "of national provisions adopted pursuant to this Directive and shall take all "
        "measures necessary to ensure that they are implemented. Penalties shall be "
        "effective, proportionate and dissuasive."
    ),
    "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2464",
}

_CSRD_ART4_CHUNK = {
    "regulation": "CSRD",
    "article": "Art.4",
    "title": "Double materiality assessment",
    "text": (
        "Undertakings subject to this Directive shall conduct a double materiality "
        "assessment to identify which sustainability topics are material from both an "
        "impact perspective and a financial materiality perspective."
    ),
    "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2464",
}

_CSRD_ART10_CHUNK = {
    "regulation": "CSRD",
    "article": "Art.10",
    "title": "Transition provisions and phased implementation",
    "text": (
        "The application of this Directive is phased: large public-interest entities "
        "with >500 employees apply from financial year 2024; other large undertakings "
        "from 2025; listed SMEs from 2026 (with opt-out until 2028)."
    ),
    "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2464",
}

_CSRD_ART1_CHUNK = {
    "regulation": "CSRD",
    "article": "Art.1",
    "title": "Subject matter and scope",
    "text": (
        "This Directive introduces mandatory sustainability reporting requirements "
        "for large companies and listed SMEs operating in the EU."
    ),
    "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2464",
}

_GDPR_ART6_CHUNK = {
    "regulation": "GDPR",
    "article": "Art.6",
    "title": "Lawfulness of processing",
    "text": (
        "Processing shall be lawful only if and to the extent that at least one of "
        "the following applies: the data subject has given consent to the processing "
        "of his or her personal data for one or more specific purposes."
    ),
    "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679",
}


# ===========================================================================
# QuestionClassifier tests
# ===========================================================================


class TestQuestionClassifier:
    def test_definition_what_is(self, classifier):
        assert classifier.classify("What is double materiality?") == QuestionType.DEFINITION

    def test_definition_define(self, classifier):
        assert classifier.classify("Define sustainability reporting.") == QuestionType.DEFINITION

    def test_applicability_does_apply(self, classifier):
        assert classifier.classify("Does CSRD apply to listed SMEs?") == QuestionType.APPLICABILITY

    def test_applicability_who_must(self, classifier):
        assert classifier.classify("Who must comply with ESRS?") == QuestionType.APPLICABILITY

    def test_requirement_what_are(self, classifier):
        qt = classifier.classify("What are the disclosure requirements under CSRD?")
        assert qt == QuestionType.REQUIREMENT

    def test_procedure_how_to(self, classifier):
        assert classifier.classify("How to comply with CSRD?") == QuestionType.PROCEDURE

    def test_timeline_when(self, classifier):
        assert classifier.classify("When does CSRD apply to listed SMEs?") == QuestionType.TIMELINE

    def test_timeline_deadline(self, classifier):
        assert classifier.classify("What is the CSRD reporting deadline?") == QuestionType.TIMELINE

    def test_comparison_difference(self, classifier):
        qt = classifier.classify("What is the difference between CSRD and ESRS?")
        assert qt == QuestionType.COMPARISON

    def test_penalty_fines(self, classifier):
        qt = classifier.classify("What are the penalties for CSRD non-compliance?")
        assert qt == QuestionType.PENALTY

    def test_general_fallback(self, classifier):
        assert classifier.classify("Tell me about sustainability.") == QuestionType.GENERAL

    def test_classify_all_returns_list(self, classifier):
        results = classifier.classify_all("What is the CSRD reporting deadline?")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_classify_all_fallback_to_general(self, classifier):
        results = classifier.classify_all("EU law")
        assert QuestionType.GENERAL in results

    def test_returns_enum_member(self, classifier):
        qt = classifier.classify("What are the penalties?")
        assert isinstance(qt, QuestionType)


# ===========================================================================
# AnswerSynthesizer tests
# ===========================================================================


class TestAnswerSynthesizer:
    def test_empty_chunks_returns_no_context_message(self, synthesizer):
        result = synthesizer.synthesize("What is CSRD?", [])
        assert "No relevant legal context" in result

    def test_definition_answer_has_irac_structure(self, synthesizer):
        result = synthesizer.synthesize("What is double materiality?", [_CSRD_ART4_CHUNK])
        assert "**Issue:**" in result
        assert "**Rule:**" in result
        assert "**Analysis:**" in result
        assert "**Conclusion:**" in result

    def test_definition_answer_contains_chunk_content(self, synthesizer):
        result = synthesizer.synthesize("What is double materiality?", [_CSRD_ART4_CHUNK])
        assert "materiality" in result.lower()

    def test_penalty_answer_contains_penalty_content(self, synthesizer):
        result = synthesizer.synthesize(
            "What are the penalties for CSRD non-compliance?", [_CSRD_ART7_CHUNK]
        )
        assert "penalt" in result.lower() or "effective" in result.lower()

    def test_timeline_answer_contains_dates(self, synthesizer):
        result = synthesizer.synthesize("When does CSRD apply?", [_CSRD_ART10_CHUNK])
        assert "2024" in result or "2025" in result or "2026" in result

    def test_requirement_answer_lists_obligations(self, synthesizer):
        result = synthesizer.synthesize(
            "What must companies disclose under CSRD?",
            [_CSRD_ART4_CHUNK, _CSRD_ART7_CHUNK],
        )
        assert "**Rule:**" in result
        assert "shall" in result.lower() or "must" in result.lower()

    def test_applicability_answer_uses_criteria(self, synthesizer):
        result = synthesizer.synthesize(
            "Does CSRD apply to listed SMEs?",
            [_CSRD_ART1_CHUNK, _CSRD_ART10_CHUNK],
        )
        assert "CSRD" in result

    def test_different_questions_produce_different_answers(self, synthesizer):
        answer_definition = synthesizer.synthesize(
            "What is a double materiality assessment?", [_CSRD_ART4_CHUNK]
        )
        answer_timeline = synthesizer.synthesize(
            "When does CSRD apply?", [_CSRD_ART10_CHUNK]
        )
        assert answer_definition != answer_timeline

    def test_different_chunks_produce_different_answers(self, synthesizer):
        answer_penalties = synthesizer.synthesize(
            "What are the key provisions?", [_CSRD_ART7_CHUNK]
        )
        answer_gdpr = synthesizer.synthesize(
            "What are the key provisions?", [_GDPR_ART6_CHUNK]
        )
        assert answer_penalties != answer_gdpr

    def test_sources_included_in_answer(self, synthesizer):
        result = synthesizer.synthesize("What is CSRD?", [_CSRD_ART1_CHUNK])
        assert "CSRD" in result

    def test_max_chunks_respected(self, synthesizer):
        many_chunks = [
            _CSRD_ART1_CHUNK, _CSRD_ART4_CHUNK, _CSRD_ART7_CHUNK,
            _CSRD_ART10_CHUNK, _GDPR_ART6_CHUNK,
        ]
        result = synthesizer.synthesize("What are the requirements?", many_chunks, max_chunks=2)
        assert result

    def test_comparison_answer_mentions_regs(self, synthesizer):
        result = synthesizer.synthesize(
            "What is the difference between CSRD and GDPR?",
            [_CSRD_ART1_CHUNK, _GDPR_ART6_CHUNK],
        )
        assert "CSRD" in result or "GDPR" in result

    def test_general_answer_has_irac_structure(self, synthesizer):
        result = synthesizer.synthesize(
            "Tell me about EU sustainability law.",
            [_CSRD_ART1_CHUNK],
        )
        assert "**Issue:**" in result

    def test_procedure_answer_has_rule_section(self, synthesizer):
        result = synthesizer.synthesize(
            "How do I comply with CSRD?",
            [_CSRD_ART4_CHUNK, _CSRD_ART7_CHUNK],
        )
        assert "**Rule:**" in result


# ===========================================================================
# FactVerifier tests
# ===========================================================================


class TestFactVerifier:
    def test_no_chunks_returns_not_grounded(self, verifier):
        result = verifier.verify("CSRD Art.7 requires penalties.", [])
        assert result.is_grounded is False
        assert result.source_coverage == 0.0

    def test_grounded_answer(self, verifier):
        answer = (
            "CSRD Art.7 requires Member States to lay down rules on penalties "
            "that are effective, proportionate and dissuasive."
        )
        result = verifier.verify(answer, [_CSRD_ART7_CHUNK])
        assert result.is_grounded is True
        assert result.source_coverage > 0.0

    def test_no_claim_sentences_treated_as_grounded(self, verifier):
        result = verifier.verify("Here is a general overview.", [_CSRD_ART1_CHUNK])
        assert result.is_grounded is True

    def test_conflict_detection_mandatory_vs_exempt(self, verifier):
        mandatory_chunk = {
            "regulation": "CSRD",
            "article": "Art.1",
            "title": "Scope",
            "text": "This Directive is mandatory for all large undertakings.",
        }
        exempt_chunk = {
            "regulation": "CSRD",
            "article": "Art.6",
            "title": "Consolidated reporting",
            "text": "Subsidiary undertakings may be exempt from individual reporting.",
        }
        answer = "CSRD Art.1 requires mandatory compliance."
        result = verifier.verify(answer, [mandatory_chunk, exempt_chunk])
        assert len(result.cross_source_conflicts) >= 1

    def test_supported_claims_populated(self, verifier):
        answer = "Member States shall lay down rules on penalties that are effective."
        result = verifier.verify(answer, [_CSRD_ART7_CHUNK])
        assert len(result.supported_claims) > 0

    def test_verification_result_fields(self, verifier):
        result = verifier.verify("Test sentence.", [_CSRD_ART1_CHUNK])
        assert hasattr(result, "is_grounded")
        assert hasattr(result, "supported_claims")
        assert hasattr(result, "unsupported_claims")
        assert hasattr(result, "cross_source_conflicts")
        assert hasattr(result, "source_coverage")

    def test_source_coverage_range(self, verifier):
        answer = (
            "CSRD shall apply. This directive is mandatory. "
            "Member States must implement penalties."
        )
        result = verifier.verify(answer, [_CSRD_ART7_CHUNK, _CSRD_ART1_CHUNK])
        assert 0.0 <= result.source_coverage <= 1.0


# ---------------------------------------------------------------------------
# is_easy_question routing helper
# ---------------------------------------------------------------------------


class TestIsEasyQuestion:
    def test_simple_definition_is_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert is_easy_question("What is CSRD?", QuestionType.DEFINITION) is True

    def test_general_no_context_is_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert is_easy_question("Tell me about EU sustainability law.", QuestionType.GENERAL) is True

    def test_applicability_not_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert is_easy_question("Does CSRD apply to us?", QuestionType.APPLICABILITY) is False

    def test_requirement_not_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert is_easy_question("What must we disclose?", QuestionType.REQUIREMENT) is False

    def test_penalty_not_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert is_easy_question("What are the fines for CSRD violations?", QuestionType.PENALTY) is False

    def test_timeline_not_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert is_easy_question("When does CSRD apply?", QuestionType.TIMELINE) is False

    def test_definition_with_employee_count_not_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert (
            is_easy_question(
                "What is CSRD and does it apply to us with 400 employees?",
                QuestionType.DEFINITION,
            )
            is False
        )

    def test_definition_with_article_ref_not_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert (
            is_easy_question(
                "What is the meaning of Article 19a CSRD?",
                QuestionType.DEFINITION,
            )
            is False
        )

    def test_general_with_turnover_not_easy(self):
        from lios.intelligence.question_classifier import QuestionType, is_easy_question

        assert (
            is_easy_question(
                "We have 80M revenue — explain sustainability law.",
                QuestionType.GENERAL,
            )
            is False
        )
