"""Orchestration engine – routes queries to features and agents."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from lios.agents.base_agent import AgentResponse, BaseAgent
from lios.agents.consensus import ConsensusEngine, ConsensusResult
from lios.logging_setup import get_logger

logger = get_logger(__name__)
from lios.agents.finance_agent import FinanceAgent
from lios.agents.sustainability_agent import SustainabilityAgent
from lios.agents.supply_chain_agent import SupplyChainAgent
from lios.config import settings
from lios.features.applicability_checker import ApplicabilityChecker, ApplicabilityResult
from lios.features.citation_engine import Citation, CitationEngine
from lios.features.compliance_roadmap import ComplianceRoadmap, ComplianceRoadmapGenerator
from lios.features.conflict_mapper import ConflictMap, ConflictMapper
from lios.features.decay_scoring import DecayScore, RegulatoryDecayScorer
from lios.features.jurisdiction_conflict import Conflict, JurisdictionConflictDetector
from lios.features.legal_breakdown import LegalBreakdown, LegalBreakdownGenerator
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.llm import LLMRefiner
from lios.orchestration.query_parser import (
    INTENT_APPLICABILITY,
    INTENT_BREAKDOWN,
    INTENT_CONFLICT,
    INTENT_GENERAL_LAW,
    INTENT_ROADMAP,
    ParsedQuery,
    QueryParser,
)
from lios.orchestration.response_aggregator import AggregatedResponse, ResponseAggregator
from lios.retrieval.hybrid_retriever import HybridRetriever
from lios.intelligence.question_classifier import (
    QuestionClassifier as _QuestionClassifier,
    is_easy_question as _is_easy_question,
)

_LLM_DIRECT_AGENT = "llm_direct"
_LLM_DIRECT_CONFIDENCE = 0.8


@dataclass
class FullResponse:
    query: str
    intent: str
    answer: str
    citations: list[Citation]
    decay_scores: list[DecayScore]
    conflicts: list[Conflict]
    consensus_result: ConsensusResult
    aggregated_response: AggregatedResponse
    roadmap: ComplianceRoadmap | None = None
    breakdown: LegalBreakdown | None = None
    applicability: ApplicabilityResult | None = None
    parsed_query: ParsedQuery | None = None
    question_type: str = "GENERAL"
    grounding_score: float = 1.0


# Intents that justify computing heavyweight decay/conflict analysis
_HEAVY_INTENTS = {INTENT_APPLICABILITY, INTENT_ROADMAP, INTENT_CONFLICT, INTENT_BREAKDOWN}


class OrchestrationEngine:
    """Central engine that coordinates all LIOS components."""

    def __init__(self) -> None:
        self.db = RegulatoryDatabase()
        self.parser = QueryParser()
        self.aggregator = ResponseAggregator()
        self.decay_scorer = RegulatoryDecayScorer(self.db)
        self.conflict_detector = JurisdictionConflictDetector()
        # Shared HybridRetriever instance – one model load, one doc-vector computation.
        self.retriever = HybridRetriever()
        self.citation_engine = CitationEngine(self.db, retriever=self.retriever)
        self.roadmap_generator = ComplianceRoadmapGenerator()
        self.applicability_checker = ApplicabilityChecker()
        self.conflict_mapper = ConflictMapper()
        self.breakdown_generator = LegalBreakdownGenerator(self.db)
        self.llm_refiner = LLMRefiner()
        self.chat_mode = settings.CHAT_MODE
        self._agent_cache: dict[str, BaseAgent] = {}
        self._question_classifier = _QuestionClassifier()

        self.consensus_engine: ConsensusEngine | None = None
        if self.chat_mode == "consensus":
            sus_agent = self._get_agent("sustainability")
            sc_agent = self._get_agent("supply_chain")
            fin_agent = self._get_agent("finance")
            self.consensus_engine = ConsensusEngine([sus_agent, sc_agent, fin_agent])

        # In-process LRU cache: keyed by MD5(query+profile), bounded to 128 entries.
        self._response_cache: dict[str, FullResponse] = {}
        self._response_cache_order: list[str] = []
        self._response_cache_maxsize = 128

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    @staticmethod
    def _make_cache_key(
        query: str,
        company_profile: dict[str, Any] | None,
        preferred_intent: str | None,
        preferred_regulation: str | None,
    ) -> str:
        """Stable hash key for identical query+profile combinations."""
        profile_str = str(sorted(company_profile.items())) if company_profile else ""
        raw = f"{query}|{profile_str}|{preferred_intent}|{preferred_regulation}"
        return hashlib.md5(raw.encode()).hexdigest()

    def route_query(
        self,
        query: str,
        company_profile: dict[str, Any] | None = None,
        jurisdictions: list[str] | None = None,
        preferred_intent: str | None = None,
        preferred_regulation: str | None = None,
        lightweight: bool | None = None,
        concise: bool = True,
    ) -> FullResponse:
        logger.info("route_query called | query=%r | intent_hint=%s", query[:80], preferred_intent)

        # LRU cache: return cached result for identical queries in the same session.
        cache_key = self._make_cache_key(query, company_profile, preferred_intent, preferred_regulation)
        if hasattr(self, "_response_cache") and cache_key in self._response_cache:
            logger.debug("route_query: cache hit for key=%s", cache_key[:8])
            return self._response_cache[cache_key]

        context: dict[str, Any] = {}
        if company_profile:
            context["company_profile"] = company_profile

        try:
            parsed = self.parser.parse(query, context)
        except Exception as exc:
            logger.error("QueryParser failed: %s", exc, exc_info=True)
            raise

        logger.debug("Parsed intent=%s regulations=%s", parsed.intent, parsed.regulations)

        # If the conversation has stabilized, bias generic follow-ups toward recent direction.
        if preferred_intent and parsed.intent == "general_query":
            parsed.intent = preferred_intent
        if preferred_regulation and not parsed.regulations:
            parsed.regulations = [preferred_regulation]

        # Classify question type once; used for routing and surfaced in the response.
        question_type = self._question_classifier.classify(query)

        # Fast path: easy definition/general questions AND general law topics answered by LLM directly.
        prefetched_chunks: list | None = None
        is_general_law = parsed.intent == INTENT_GENERAL_LAW
        if (
            is_general_law
            or (
                parsed.intent in {"general_query", "legal_breakdown"}
                and _is_easy_question(query, question_type)
            )
        ):
            direct_answer, prefetched_chunks = self._try_llm_direct(query)
            if direct_answer is not None:
                logger.debug("route_query: returning easy-path LLM-direct answer.")
                easy_response = FullResponse(
                    query=query,
                    intent=parsed.intent,
                    answer=direct_answer,
                    citations=[],
                    decay_scores=[],
                    conflicts=[],
                    consensus_result=self._build_single_agent_consensus(
                        AgentResponse(
                            agent_name=_LLM_DIRECT_AGENT,
                            answer=direct_answer,
                            citations=[],
                            confidence=_LLM_DIRECT_CONFIDENCE,
                            reasoning="Answered directly by LLM without agent analysis.",
                        )
                    ),
                    aggregated_response=AggregatedResponse(
                        answer=direct_answer,
                        citations=[],
                        consensus_score=1.0,
                        agent_count=1,
                        agreeing_agents=[_LLM_DIRECT_AGENT],
                        diverging_agents=[],
                    ),
                    roadmap=None,
                    breakdown=None,
                    applicability=None,
                    parsed_query=parsed,
                    question_type=question_type.value,
                    grounding_score=_LLM_DIRECT_CONFIDENCE,
                )
                self._cache_response(cache_key, easy_response)
                return easy_response

        use_lightweight = self._should_use_lightweight(
            parsed=parsed,
            company_profile=company_profile,
            jurisdictions=jurisdictions,
            lightweight=lightweight,
        )

        # Merge jurisdictions from args + parsed
        all_jurisdictions = list(dict.fromkeys(
            (jurisdictions or []) + parsed.jurisdictions
        ))
        all_regulations = parsed.regulations or list(self.db.REGULATION_MODULES.keys())

        try:
            primary_agent = self._select_primary_agent(parsed, query)
            primary_response = primary_agent.analyze(query, context)
            logger.debug("Primary agent %s responded (confidence=%.2f)", primary_agent.name, primary_response.confidence)
        except Exception as exc:
            logger.error("Primary agent analysis failed: %s", exc, exc_info=True)
            primary_response = AgentResponse(
                agent_name="fallback",
                answer="Agent analysis temporarily unavailable. Please try again.",
                citations=[],
                confidence=0.1,
                reasoning=str(exc),
            )

        # Keep the first chat simple by default; consensus remains available when enabled.
        if self.consensus_engine is not None:
            try:
                consensus_result = self.consensus_engine.run(query, context)
                logger.debug("Consensus reached=%s confidence=%.2f", consensus_result.consensus_reached, consensus_result.confidence)
            except Exception as exc:
                logger.warning("ConsensusEngine failed, falling back to single-agent: %s", exc)
                consensus_result = self._build_single_agent_consensus(primary_response)
        else:
            consensus_result = self._build_single_agent_consensus(primary_response)

        # Run aggregator
        try:
            aggregated = self.aggregator.aggregate(consensus_result.agent_responses)
        except Exception as exc:
            logger.warning("ResponseAggregator failed, using empty aggregation: %s", exc)
            aggregated = AggregatedResponse(summary="", key_points=[], confidence=0.0)

        # Heavy analysis (decay/conflict) only runs for intents that need it.
        # Chat queries skip this to keep latency low.
        run_heavy = not use_lightweight and parsed.intent in _HEAVY_INTENTS

        decay_scores = []
        if run_heavy:
            try:
                decay_scores = [
                    self.decay_scorer.decay_score(reg)
                    for reg in (parsed.regulations or list(self.db.REGULATION_MODULES.keys()))
                ]
            except Exception as exc:
                logger.warning("DecayScorer failed: %s", exc)

        # Jurisdiction conflicts
        jur_conflicts: list[Conflict] = []
        if run_heavy:
            try:
                if all_jurisdictions:
                    for reg in all_regulations:
                        jur_conflicts.extend(
                            self.conflict_detector.detect_conflicts(reg, all_jurisdictions)
                        )
                else:
                    jur_conflicts = self.conflict_detector.get_all_known_conflicts()[:3]
            except Exception as exc:
                logger.warning("JurisdictionConflictDetector failed: %s", exc)

        # Citations
        try:
            citations = self.citation_engine.get_citations(
                query,
                regulations=parsed.regulations if parsed.regulations else None,
            )
        except Exception as exc:
            logger.warning("CitationEngine failed: %s", exc)
            citations = []

        # Retrieve BM25 context chunks for the LLM prompt (reuse easy-path chunks when available)
        rag_context = ""
        try:
            chunks_for_context = prefetched_chunks or self.retriever.search(query, top_k=5)
            if chunks_for_context:
                rag_context = self.retriever.format_context(chunks_for_context)
        except Exception as exc:
            logger.warning("HybridRetriever.search failed: %s", exc)

        # Intent-specific extras
        roadmap: ComplianceRoadmap | None = None
        breakdown: LegalBreakdown | None = None
        applicability: ApplicabilityResult | None = None
        effective_company_profile = company_profile or parsed.company_profile

        if parsed.intent == INTENT_ROADMAP and effective_company_profile:
            try:
                roadmap = self.roadmap_generator.generate_roadmap(effective_company_profile)
            except Exception as exc:
                logger.warning("RoadmapGenerator failed: %s", exc)

        elif parsed.intent == INTENT_APPLICABILITY and effective_company_profile:
            reg = (parsed.regulations[0] if parsed.regulations else "CSRD")
            try:
                applicability = self.applicability_checker.check_applicability(
                    reg, effective_company_profile
                )
            except Exception as exc:
                logger.warning("ApplicabilityChecker failed for %s: %s", reg, exc)

        elif parsed.intent == INTENT_BREAKDOWN and parsed.regulations:
            reg = parsed.regulations[0]
            try:
                breakdown = self.breakdown_generator.generate_breakdown(query, reg)
            except Exception as exc:
                logger.warning("BreakdownGenerator failed for %s: %s", reg, exc)

        # Build final answer
        answer = self._build_final_answer(
            parsed,
            consensus_result,
            applicability,
            roadmap,
            breakdown,
            primary_response,
        )

        # LLM handles formatting and conciseness when enabled.
        # Fall back to rule-based concision only when LLM is off.
        if concise and not self.llm_refiner.enabled:
            answer = self._make_concise_answer(
                draft=answer,
                intent=parsed.intent,
                citations=citations,
            )

        try:
            answer = self.llm_refiner.refine(
                query=query,
                draft_answer=answer,
                context={
                    "intent": parsed.intent,
                    "regulations": parsed.regulations,
                    "jurisdictions": all_jurisdictions,
                    "lightweight": use_lightweight,
                    "rag_context": rag_context,
                },
            )
        except Exception as exc:
            logger.warning("LLMRefiner failed, using draft answer: %s", exc)

        # Compute a grounding score from the consensus confidence.
        grounding_score = round(consensus_result.confidence, 3)

        logger.info(
            "route_query done | intent=%s | citations=%d | conflicts=%d | grounding=%.2f",
            parsed.intent,
            len(citations),
            len(jur_conflicts),
            grounding_score,
        )

        full_response = FullResponse(
            query=query,
            intent=parsed.intent,
            answer=answer,
            citations=citations,
            decay_scores=decay_scores,
            conflicts=jur_conflicts,
            consensus_result=consensus_result,
            aggregated_response=aggregated,
            roadmap=roadmap,
            breakdown=breakdown,
            applicability=applicability,
            parsed_query=parsed,
            question_type=question_type.value,
            grounding_score=grounding_score,
        )
        self._cache_response(cache_key, full_response)
        return full_response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_final_answer(
        self,
        parsed: ParsedQuery,
        consensus: ConsensusResult,
        applicability: ApplicabilityResult | None,
        roadmap: ComplianceRoadmap | None,
        breakdown: LegalBreakdown | None,
        primary_response: AgentResponse | None = None,
    ) -> str:
        parts: list[str] = []

        if applicability:
            status = "✅ APPLICABLE" if applicability.applicable else "❌ NOT APPLICABLE"
            parts.append(f"## Applicability: {status}\n{applicability.reason}")

        if roadmap:
            parts.append(f"## Compliance Roadmap\n{roadmap.summary}")
            for step in roadmap.steps[:5]:
                parts.append(
                    f"  {step.step_number}. [{step.priority.upper()}] {step.title} "
                    f"(deadline: {step.deadline})"
                )

        if breakdown:
            parts.append(f"## Legal Breakdown: {breakdown.regulation}\n{breakdown.summary}")

        if len(consensus.agent_responses) == 1 and primary_response is not None:
            parts.append(primary_response.answer)
        elif consensus.consensus_reached:
            parts.append(f"## Consensus Answer (confidence: {consensus.confidence:.0%})")
            parts.append(consensus.answer)
        else:
            parts.append("## ⚠️ No Consensus")
            parts.append(consensus.conflict_report)

        return "\n\n".join(parts)

    def _build_single_agent_consensus(self, response: AgentResponse) -> ConsensusResult:
        return ConsensusResult(
            consensus_reached=True,
            answer=response.answer,
            citations=response.citations,
            conflict_report="",
            agent_responses=[response],
            confidence=response.confidence,
            agreeing_agents=[response.agent_name],
        )

    def _should_use_lightweight(
        self,
        parsed: ParsedQuery,
        company_profile: dict[str, Any] | None,
        jurisdictions: list[str] | None,
        lightweight: bool | None,
    ) -> bool:
        if lightweight is not None:
            return lightweight

        has_company_context = bool(company_profile)
        has_jurisdictions = bool(jurisdictions)
        return (
            not has_company_context
            and not has_jurisdictions
            and parsed.intent in {"general_query", "legal_breakdown"}
        )

    def _try_llm_direct(self, query: str) -> tuple[str | None, list]:
        """Call Ollama directly (no corpus context), verify grounding.

        Returns (answer, top_chunks) on success or (None, top_chunks) on failure
        so the caller can reuse the already-fetched RetrievedChunk list in the
        full RAG pipeline instead of retrieving a second time.
        """
        if not settings.LLM_ENABLED:
            return None, []

        from lios.intelligence.fact_verifier import FactVerifier
        from lios.llm.ollama_client import call_ollama_sync
        from lios.reasoning.legal_reasoner import build_direct_prompt
        from lios.orchestration.query_parser import INTENT_GENERAL_LAW as _INTENT_GL

        # Detect topic area from a parsed query if available
        _topic = "general_law" if self.parser.parse(query).intent == _INTENT_GL else "eu_regulatory"
        try:
            llm_answer = call_ollama_sync(build_direct_prompt(query, topic_area=_topic))
        except Exception as exc:  # noqa: BLE001
            logger.debug("LLM-direct call failed: %s", exc)
            return None, []

        try:
            top_chunks = self.retriever.search(query, top_k=5)
            raw_chunks = [rc.chunk for rc in top_chunks]
            if raw_chunks:
                result = FactVerifier().verify(llm_answer, raw_chunks)
                if result.is_grounded:
                    return llm_answer, top_chunks
                logger.debug(
                    "LLM-direct answer not grounded (%.2f); falling back to full pipeline.",
                    result.source_coverage,
                )
                return None, top_chunks
            return llm_answer, []  # no corpus — trust the LLM
        except Exception as exc:  # noqa: BLE001
            logger.debug("Corpus verification failed: %s", exc)
            return None, []

    def _cache_response(self, key: str, response: FullResponse) -> None:
        """Store response in the in-process LRU cache, evicting oldest when full."""
        if key in self._response_cache:
            return
        if len(self._response_cache_order) >= self._response_cache_maxsize:
            oldest = self._response_cache_order.pop(0)
            self._response_cache.pop(oldest, None)
        self._response_cache[key] = response
        self._response_cache_order.append(key)

    def _get_agent(self, name: str) -> "BaseAgent":
        """Return a cached agent instance by short name, creating it on first call."""
        if name in self._agent_cache:
            return self._agent_cache[name]

        agent: "BaseAgent"
        if name == "sustainability":
            agent = SustainabilityAgent()
        elif name == "supply_chain":
            agent = SupplyChainAgent()
        elif name == "finance":
            agent = FinanceAgent()
        else:
            from lios.agents.unified_agent import UnifiedComplianceAgent
            agent = UnifiedComplianceAgent()

        self._agent_cache[name] = agent
        return agent

    def _select_primary_agent(self, parsed: "ParsedQuery", query: str) -> "BaseAgent":
        """Select the most appropriate primary agent for this query."""
        regs = {r.upper() for r in (parsed.regulations or [])}
        q_lower = query.lower()

        # Finance-specific regulation or keywords
        if "SFDR" in regs or any(kw in q_lower for kw in ("sfdr", "pai", "principal adverse", "article 8", "article 9")):
            return self._get_agent("finance")

        # Supply chain keywords
        if any(kw in q_lower for kw in ("supply chain", "due diligence", "cs3d", "csddd", "supplier", "upstream")):
            return self._get_agent("supply_chain")

        # Default: unified compliance agent covers everything else
        return self._get_agent("unified")

    def _make_concise_answer(
        self,
        draft: str,
        intent: str,
        citations: list[Citation],
    ) -> str:
        # Keep detailed structure for action/assessment workflows.
        if intent in {"compliance_roadmap", "applicability_check"}:
            return draft

        lines = [ln.strip() for ln in draft.splitlines() if ln.strip() and not ln.strip().startswith("##")]
        text = " ".join(lines)
        text = re.sub(r"\[[^\]]+\]:\s*", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        sentences = re.split(r"(?<=[.!?])\s+", text)
        selected: list[str] = []
        total = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) < 25:
                continue
            selected.append(sentence)
            total += len(sentence)
            if len(selected) >= 5 or total >= 800:
                break

        concise = " ".join(selected) if selected else text[:800]

        if citations:
            top = citations[:2]
            sources = " | ".join(f"{c.regulation} {c.article_id}: {c.url}" for c in top)
            concise = f"{concise}\n\nSources: {sources}"

        return concise
