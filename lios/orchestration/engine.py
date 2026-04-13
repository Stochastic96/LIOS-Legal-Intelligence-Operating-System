"""Orchestration engine – routes queries to features and agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lios.agents.consensus import ConsensusEngine, ConsensusResult
from lios.agents.finance_agent import FinanceAgent
from lios.agents.sustainability_agent import SustainabilityAgent
from lios.agents.supply_chain_agent import SupplyChainAgent
from lios.features.applicability_checker import ApplicabilityChecker, ApplicabilityResult
from lios.features.citation_engine import Citation, CitationEngine
from lios.features.compliance_roadmap import ComplianceRoadmap, ComplianceRoadmapGenerator
from lios.features.conflict_mapper import ConflictMap, ConflictMapper
from lios.features.decay_scoring import DecayScore, RegulatoryDecayScorer
from lios.features.jurisdiction_conflict import Conflict, JurisdictionConflictDetector
from lios.features.legal_breakdown import LegalBreakdown, LegalBreakdownGenerator
from lios.knowledge.regulatory_db import RegulatoryDatabase
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

        # Build agents
        sus_agent = SustainabilityAgent(self.db)
        sc_agent = SupplyChainAgent(self.db)
        fin_agent = FinanceAgent(self.db)
        self.consensus_engine = ConsensusEngine([sus_agent, sc_agent, fin_agent])

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def route_query(
        self,
        query: str,
        company_profile: dict[str, Any] | None = None,
        jurisdictions: list[str] | None = None,
    ) -> FullResponse:
        context: dict[str, Any] = {}
        if company_profile:
            context["company_profile"] = company_profile

        parsed = self.parser.parse(query, context)

        # Merge jurisdictions from args + parsed
        all_jurisdictions = list(dict.fromkeys(
            (jurisdictions or []) + parsed.jurisdictions
        ))
        all_regulations = parsed.regulations or list(self.db.REGULATION_MODULES.keys())

        # Run three-agent consensus
        consensus_result = self.consensus_engine.run(query, context)

        # Run aggregator
        aggregated = self.aggregator.aggregate(consensus_result.agent_responses)

        # Decay scores for detected (or all) regulations
        decay_scores = [
            self.decay_scorer.decay_score(reg)
            for reg in (parsed.regulations or list(self.db.REGULATION_MODULES.keys()))
        ]

        # Jurisdiction conflicts
        jur_conflicts: list[Conflict] = []
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
            parsed, consensus_result, applicability, roadmap, breakdown
        )

        return FullResponse(
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

        if consensus.consensus_reached:
            parts.append(f"## Consensus Answer (confidence: {consensus.confidence:.0%})")
            parts.append(consensus.answer)
        else:
            parts.append("## ⚠️ No Consensus")
            parts.append(consensus.conflict_report)

        return "\n\n".join(parts)
