"""Tests for orchestration engine, query parser, and response aggregator."""

from __future__ import annotations

import pytest

from lios.orchestration.engine import FullResponse, OrchestrationEngine
from lios.orchestration.query_parser import (
    INTENT_APPLICABILITY,
    INTENT_BREAKDOWN,
    INTENT_CONFLICT,
    INTENT_GENERAL,
    INTENT_ROADMAP,
    ParsedQuery,
    QueryParser,
)
from lios.orchestration.response_aggregator import AggregatedResponse, ResponseAggregator
from lios.agents.base_agent import AgentResponse


# ------------------------------------------------------------------ #
# QueryParser Tests
# ------------------------------------------------------------------ #

class TestQueryParser:
    @pytest.fixture
    def parser(self):
        return QueryParser()

    def test_parse_returns_parsed_query(self, parser):
        result = parser.parse("Does CSRD apply to us?")
        assert isinstance(result, ParsedQuery)

    def test_parse_detects_csrd(self, parser):
        result = parser.parse("What are CSRD requirements?")
        assert "CSRD" in result.regulations

    def test_parse_detects_sfdr(self, parser):
        result = parser.parse("SFDR article 8 fund classification")
        assert "SFDR" in result.regulations

    def test_parse_detects_esrs(self, parser):
        result = parser.parse("ESRS E1 climate change disclosure")
        assert "ESRS" in result.regulations

    def test_parse_detects_eu_taxonomy(self, parser):
        result = parser.parse("How to assess EU Taxonomy alignment?")
        assert "EU_TAXONOMY" in result.regulations

    def test_parse_intent_applicability(self, parser):
        result = parser.parse("Does CSRD apply to our company?")
        assert result.intent == INTENT_APPLICABILITY

    def test_parse_intent_roadmap(self, parser):
        result = parser.parse("What are the steps to comply with CSRD?")
        assert result.intent == INTENT_ROADMAP

    def test_parse_intent_breakdown(self, parser):
        result = parser.parse("Explain the CSRD reporting obligations")
        assert result.intent == INTENT_BREAKDOWN

    def test_parse_intent_conflict(self, parser):
        result = parser.parse("Are there conflicts between CSRD and German HGB?")
        assert result.intent == INTENT_CONFLICT

    def test_parse_intent_general_fallback(self, parser):
        result = parser.parse("Tell me something about sustainability")
        # Should not crash, should return some intent
        assert result.intent in {
            INTENT_APPLICABILITY, INTENT_ROADMAP, INTENT_BREAKDOWN,
            INTENT_CONFLICT, INTENT_GENERAL
        }

    def test_parse_detects_germany(self, parser):
        result = parser.parse("CSRD and German HGB conflict analysis")
        assert "Germany" in result.jurisdictions

    def test_parse_detects_france(self, parser):
        result = parser.parse("How does loi PACTE relate to EU Taxonomy in France?")
        assert "France" in result.jurisdictions

    def test_parse_extracts_keywords(self, parser):
        result = parser.parse("CSRD sustainability reporting for large companies")
        assert isinstance(result.keywords, list)
        assert len(result.keywords) > 0

    def test_parse_employee_count_extraction(self, parser):
        result = parser.parse("We have 600 employees, does CSRD apply?")
        assert result.company_profile.get("employees") == 600

    def test_parse_stores_raw_query(self, parser):
        q = "Does EU Taxonomy apply to banks?"
        result = parser.parse(q)
        assert result.raw_query == q

    def test_parse_context_company_profile(self, parser):
        ctx = {"company_profile": {"employees": 800, "sector": "finance"}}
        result = parser.parse("SFDR obligations", context=ctx)
        assert result.company_profile.get("employees") == 800


# ------------------------------------------------------------------ #
# ResponseAggregator Tests
# ------------------------------------------------------------------ #

class TestResponseAggregator:
    @pytest.fixture
    def aggregator(self):
        return ResponseAggregator()

    def _make_response(self, name, keywords, citations=None, confidence=0.7):
        return AgentResponse(
            agent_name=name,
            answer=f"Answer from {name}",
            citations=citations or [],
            confidence=confidence,
            reasoning=f"Reasoning from {name}",
            conclusion_keywords=keywords,
        )

    def test_aggregate_returns_dataclass(self, aggregator):
        responses = [
            self._make_response("a1", ["applies"]),
            self._make_response("a2", ["applies"]),
            self._make_response("a3", ["applies"]),
        ]
        result = aggregator.aggregate(responses)
        assert isinstance(result, AggregatedResponse)

    def test_aggregate_full_consensus(self, aggregator):
        responses = [
            self._make_response("a1", ["applies"]),
            self._make_response("a2", ["applies"]),
            self._make_response("a3", ["applies"]),
        ]
        result = aggregator.aggregate(responses)
        assert result.consensus_score == 1.0

    def test_aggregate_partial_consensus(self, aggregator):
        responses = [
            self._make_response("a1", ["applies"]),
            self._make_response("a2", ["applies"]),
            self._make_response("a3", ["exemption"]),
        ]
        result = aggregator.aggregate(responses)
        assert result.consensus_score > 0.5

    def test_aggregate_no_consensus(self, aggregator):
        responses = [
            self._make_response("a1", ["applies"]),
            self._make_response("a2", ["exemption"]),
            self._make_response("a3", ["unclear"]),
        ]
        result = aggregator.aggregate(responses)
        assert result.consensus_score < 1.0

    def test_aggregate_citations_deduped(self, aggregator):
        citations = [{"regulation": "CSRD", "article_id": "Art.1"}]
        responses = [
            self._make_response("a1", ["applies"], citations=citations),
            self._make_response("a2", ["applies"], citations=citations),
            self._make_response("a3", ["applies"], citations=citations),
        ]
        result = aggregator.aggregate(responses)
        keys = [f"{c['regulation']}:{c['article_id']}" for c in result.citations]
        assert len(keys) == len(set(keys))

    def test_aggregate_empty_returns_default(self, aggregator):
        result = aggregator.aggregate([])
        assert result.consensus_score == 0.0
        assert result.agent_count == 0

    def test_aggregate_agent_count(self, aggregator):
        responses = [
            self._make_response("a1", ["applies"]),
            self._make_response("a2", ["applies"]),
            self._make_response("a3", ["applies"]),
        ]
        result = aggregator.aggregate(responses)
        assert result.agent_count == 3


# ------------------------------------------------------------------ #
# OrchestrationEngine Tests
# ------------------------------------------------------------------ #

class TestOrchestrationEngine:
    @pytest.fixture(scope="class")
    def engine(self):
        return OrchestrationEngine()

    def test_route_query_returns_full_response(self, engine):
        result = engine.route_query("Does CSRD apply to large companies?")
        assert isinstance(result, FullResponse)

    def test_route_query_has_answer(self, engine):
        result = engine.route_query("What is CSRD?")
        assert result.answer
        assert len(result.answer) > 10

    def test_route_query_has_decay_scores(self, engine):
        result = engine.route_query("CSRD reporting requirements")
        assert len(result.decay_scores) > 0

    def test_route_query_has_citations(self, engine):
        result = engine.route_query("CSRD double materiality assessment")
        assert isinstance(result.citations, list)

    def test_route_query_applicability_intent(self, engine, sample_company_profile):
        result = engine.route_query(
            "Does CSRD apply to us?",
            company_profile=sample_company_profile,
        )
        assert result.intent == INTENT_APPLICABILITY
        assert result.applicability is not None
        assert result.applicability.applicable is True

    def test_route_query_roadmap_intent(self, engine, sample_company_profile):
        result = engine.route_query(
            "What steps do we need to take to comply with CSRD?",
            company_profile=sample_company_profile,
        )
        assert result.intent == INTENT_ROADMAP
        assert result.roadmap is not None
        assert len(result.roadmap.steps) > 0

    def test_route_query_with_jurisdictions(self, engine):
        result = engine.route_query(
            "CSRD conflicts with national law",
            jurisdictions=["Germany"],
        )
        # Should detect German conflicts
        assert isinstance(result.conflicts, list)

    def test_route_query_consensus_result(self, engine):
        result = engine.route_query("ESRS E1 climate disclosure")
        assert result.consensus_result is not None
        assert isinstance(result.consensus_result.consensus_reached, bool)

    def test_route_query_parsed_query_stored(self, engine):
        result = engine.route_query("SFDR article 9 fund requirements")
        assert result.parsed_query is not None
        assert result.parsed_query.raw_query == "SFDR article 9 fund requirements"

    def test_route_query_stores_intent(self, engine):
        result = engine.route_query("Explain CSRD penalties")
        assert result.intent in {
            INTENT_APPLICABILITY, INTENT_ROADMAP, INTENT_BREAKDOWN,
            INTENT_CONFLICT, INTENT_GENERAL
        }
