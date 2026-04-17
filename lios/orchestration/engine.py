"""Orchestration engine – routes queries to features and agents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from lios.agents.base_agent import AgentResponse, BaseAgent
from lios.agents.consensus import ConsensusEngine, ConsensusResult
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
    INTENT_ROADMAP,
    ParsedQuery,
    QueryParser,
)
from lios.orchestration.response_aggregator import AggregatedResponse, ResponseAggregator


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
    trust_label: str = ""
    roadmap: ComplianceRoadmap | None = None
    breakdown: LegalBreakdown | None = None
    applicability: ApplicabilityResult | None = None
    parsed_query: ParsedQuery | None = None


class OrchestrationEngine:
    """Central engine that coordinates all LIOS components."""

    def __init__(self) -> None:
        self.db = RegulatoryDatabase()
        self.parser = QueryParser()
        self.aggregator = ResponseAggregator()
        self.decay_scorer = RegulatoryDecayScorer(self.db)
        self.conflict_detector = JurisdictionConflictDetector()
        self.citation_engine = CitationEngine(self.db)
        self.roadmap_generator = ComplianceRoadmapGenerator()
        self.applicability_checker = ApplicabilityChecker()
        self.conflict_mapper = ConflictMapper()
        self.breakdown_generator = LegalBreakdownGenerator(self.db)
        self.llm_refiner = LLMRefiner()
        self.chat_mode = settings.CHAT_MODE
        self._agent_cache: dict[str, BaseAgent] = {}

        self.consensus_engine: ConsensusEngine | None = None
        if self.chat_mode == "consensus":
            sus_agent = self._get_agent("sustainability")
            sc_agent = self._get_agent("supply_chain")
            fin_agent = self._get_agent("finance")
            self.consensus_engine = ConsensusEngine([sus_agent, sc_agent, fin_agent])

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

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
        context: dict[str, Any] = {}
        if company_profile:
            context["company_profile"] = company_profile

        parsed = self.parser.parse(query, context)

        # If the conversation has stabilized, bias generic follow-ups toward recent direction.
        if preferred_intent and parsed.intent == "general_query":
            parsed.intent = preferred_intent
        if preferred_regulation and not parsed.regulations:
            parsed.regulations = [preferred_regulation]

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

        primary_agent = self._select_primary_agent(parsed, query)
        primary_response = primary_agent.analyze(query, context)

        # Keep the first chat simple by default; consensus remains available when enabled.
        if self.consensus_engine is not None:
            consensus_result = self.consensus_engine.run(query, context)
        else:
            consensus_result = self._build_single_agent_consensus(primary_response)

        # Run aggregator
        aggregated = self.aggregator.aggregate(consensus_result.agent_responses)

        # Heavy analysis is skipped for lightweight/direct definition flows.
        if use_lightweight:
            decay_scores = []
        else:
            decay_scores = [
                self.decay_scorer.decay_score(reg)
                for reg in (parsed.regulations or list(self.db.REGULATION_MODULES.keys()))
            ]

        # Jurisdiction conflicts
        jur_conflicts: list[Conflict] = []
        if not use_lightweight:
            if all_jurisdictions:
                for reg in all_regulations:
                    jur_conflicts.extend(
                        self.conflict_detector.detect_conflicts(reg, all_jurisdictions)
                    )
            else:
                jur_conflicts = self.conflict_detector.get_all_known_conflicts()[:3]

        # Citations
        citations = self.citation_engine.get_citations(
            query,
            regulations=parsed.regulations if parsed.regulations else None,
        )

        # Intent-specific extras
        roadmap: ComplianceRoadmap | None = None
        breakdown: LegalBreakdown | None = None
        applicability: ApplicabilityResult | None = None
        effective_company_profile = company_profile or parsed.company_profile

        if parsed.intent == INTENT_ROADMAP and effective_company_profile:
            roadmap = self.roadmap_generator.generate_roadmap(effective_company_profile)

        elif parsed.intent == INTENT_APPLICABILITY and effective_company_profile:
            reg = (parsed.regulations[0] if parsed.regulations else "CSRD")
            applicability = self.applicability_checker.check_applicability(
                reg, effective_company_profile
            )

        elif parsed.intent == INTENT_BREAKDOWN and parsed.regulations:
            reg = parsed.regulations[0]
            breakdown = self.breakdown_generator.generate_breakdown(query, reg)

        # Build final answer
        answer = self._build_final_answer(
            parsed,
            consensus_result,
            applicability,
            roadmap,
            breakdown,
            primary_response,
        )
        if concise:
            answer = self._make_concise_answer(
                draft=answer,
                intent=parsed.intent,
                citations=citations,
            )

        answer = self.llm_refiner.refine(
            query=query,
            draft_answer=answer,
            context={
                "intent": parsed.intent,
                "regulations": parsed.regulations,
                "jurisdictions": all_jurisdictions,
                "lightweight": use_lightweight,
            },
        )

        trust_label = self._build_trust_label(decay_scores, citations, self.db)

        return FullResponse(
            query=query,
            intent=parsed.intent,
            answer=answer,
            citations=citations,
            decay_scores=decay_scores,
            conflicts=jur_conflicts,
            consensus_result=consensus_result,
            aggregated_response=aggregated,
            trust_label=trust_label,
            roadmap=roadmap,
            breakdown=breakdown,
            applicability=applicability,
            parsed_query=parsed,
        )

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
            parts.append(consensus.answer)
        else:
            parts.append(consensus.conflict_report)

        return "\n\n".join(parts)

    def _get_agent(self, name: str) -> BaseAgent:
        if name in self._agent_cache:
            return self._agent_cache[name]

        if name == "sustainability":
            agent: BaseAgent = SustainabilityAgent(self.db)
        elif name == "supply_chain":
            agent = SupplyChainAgent(self.db)
        elif name == "finance":
            agent = FinanceAgent(self.db)
        else:
            raise KeyError(f"Unknown agent: {name}")

        self._agent_cache[name] = agent
        return agent

    def _select_primary_agent(self, parsed: ParsedQuery, query: str) -> BaseAgent:
        query_lower = query.lower()

        if any(keyword in query_lower for keyword in ["supply chain", "supplier", "due diligence", "value chain"]):
            return self._get_agent("supply_chain")

        if any(reg in {"SFDR", "EU_TAXONOMY"} for reg in parsed.regulations):
            return self._get_agent("finance")

        return self._get_agent("sustainability")

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

        # Without company context or jurisdiction filtering, decay scores and
        # conflict scanning add latency without providing value to the user.
        has_company_context = bool(company_profile)
        has_jurisdictions = bool(jurisdictions) or bool(parsed.jurisdictions)
        return not has_company_context and not has_jurisdictions

    def _build_trust_label(
        self,
        decay_scores: list[DecayScore],
        citations: list[Citation],
        db: RegulatoryDatabase,
    ) -> str:
        """Return a human-readable trust label for the answer."""
        citation_count = len(citations)

        if decay_scores:
            avg_score = sum(d.score for d in decay_scores) / len(decay_scores)
            freshness = "Current" if avg_score >= 80 else "Aging" if avg_score >= 60 else "Review Recommended"
            freshest = max(decay_scores, key=lambda d: d.score)
            date_note = f"data as of {freshest.last_updated}"
        else:
            # Derive freshness from the regulations referenced in citations
            reg_keys = list(dict.fromkeys(c.regulation for c in citations[:3]))
            dates: list[str] = []
            for key in reg_keys:
                reg = db.get_regulation(key)
                if reg:
                    dates.append(reg.get("last_updated", ""))
            if dates:
                non_empty = [d for d in dates if d]
                if non_empty:
                    latest = max(non_empty)
                    date_note = f"data as of {latest}"
                    freshness = "Current"
                else:
                    date_note = "data freshness unknown"
                    freshness = "Review Recommended"
            else:
                date_note = "data freshness unknown"
                freshness = "Review Recommended"

        if citation_count >= 3 and freshness == "Current":
            return f"✅ High Confidence — {citation_count} source articles cited, {date_note}"
        elif citation_count >= 1 and freshness != "Review Recommended":
            return f"✅ Verified — {citation_count} source article{'s' if citation_count != 1 else ''} cited, {date_note}"
        else:
            return f"⚠️ Review Recommended — {citation_count} source article{'s' if citation_count != 1 else ''} cited, {date_note}"

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
            if len(selected) >= 2 or total >= 380:
                break

        concise = " ".join(selected) if selected else text[:380]

        if citations:
            top = citations[:3]
            citation_lines = "\n".join(
                f"📎 {c.regulation} {c.article_id} — {c.url}" for c in top
            )
            concise = f"{concise}\n\n{citation_lines}"

        return concise
