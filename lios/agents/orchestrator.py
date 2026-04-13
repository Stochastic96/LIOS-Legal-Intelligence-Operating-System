"""
Orchestration engine – the brain of LIOS.

Coordinates knowledge base retrieval, specialist agent dispatch,
consensus evaluation, and feature enrichment into a single response object.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from lios.agents.base_agent import AgentResponse
from lios.agents.consensus import ConsensusEngine, ConsensusResult
from lios.agents.features.citation_engine import CitationEngine
from lios.agents.features.conflict_mapper import ConflictMapper
from lios.agents.features.decay_scoring import DecayScorer
from lios.agents.specialists.finance_agent import FinanceAgent
from lios.agents.specialists.supply_chain_agent import SupplyChainAgent
from lios.agents.specialists.sustainability_agent import SustainabilityAgent
from lios.database.connection import AsyncSessionFactory
from lios.database.repositories.query_repo import QueryORM, QueryRepository
from lios.knowledge_base.manager import KnowledgeBaseManager
from lios.utils.helpers import utcnow
from lios.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrchestratorResponse:
    query_id: str
    query: str
    answer: Optional[str]               # None when consensus fails
    consensus_reached: bool
    consensus_score: float
    decay_score: Optional[float]
    decay_label: Optional[str]
    decay_warning: Optional[str]
    conflict_summary: Optional[str]
    jurisdiction_conflicts: list[dict]
    citations: list[dict]
    agent_responses: dict[str, str]
    created_at: datetime = field(default_factory=utcnow)


class Orchestrator:
    """
    Top-level orchestrator for LIOS query resolution.

    Flow
    ----
    1. Retrieve relevant chunks from the knowledge base (semantic search)
    2. Fan out to three specialist agents in parallel
    3. Run consensus engine
    4. Enrich with decay scoring, jurisdiction conflicts, citations
    5. Persist to SQLite
    6. Return structured response
    """

    def __init__(
        self,
        kb: Optional[KnowledgeBaseManager] = None,
        consensus_engine: Optional[ConsensusEngine] = None,
        decay_scorer: Optional[DecayScorer] = None,
        citation_engine: Optional[CitationEngine] = None,
        conflict_mapper: Optional[ConflictMapper] = None,
    ) -> None:
        self._kb = kb or KnowledgeBaseManager()
        self._agents = [
            SustainabilityAgent(),
            SupplyChainAgent(),
            FinanceAgent(),
        ]
        self._consensus = consensus_engine or ConsensusEngine()
        self._decay = decay_scorer or DecayScorer()
        self._citations = citation_engine or CitationEngine()
        self._conflicts = conflict_mapper or ConflictMapper()

    async def handle(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        top_k: int = 5,
    ) -> OrchestratorResponse:
        query_id = str(uuid.uuid4())
        logger.info("[%s] Processing query: %s", query_id, query[:80])

        # ── 1. Retrieve context ───────────────────────────────────────────────
        search_results = self._kb.search(query, top_k=top_k)
        context_chunks = [r.text for r in search_results]
        last_verified_dates = [
            r.metadata.get("last_verified_at") for r in search_results
        ]
        logger.debug("[%s] Retrieved %d chunks", query_id, len(context_chunks))

        # ── 2. Agent fan-out ──────────────────────────────────────────────────
        agent_responses: list[AgentResponse] = []
        for agent in self._agents:
            try:
                resp = await agent.respond(query, context_chunks)
                agent_responses.append(resp)
            except Exception as exc:
                logger.warning("[%s] Agent %s failed: %s", query_id, agent.agent_id, exc)

        # ── 3. Consensus ──────────────────────────────────────────────────────
        consensus: ConsensusResult = self._consensus.evaluate(agent_responses)

        # ── 4. Feature enrichment ─────────────────────────────────────────────
        # Decay scoring
        decay = self._decay.aggregate(last_verified_dates)

        # Citation enrichment
        rich_citations = self._citations.enrich(consensus.citations)
        citation_dicts = [c.to_dict() for c in rich_citations]

        # Jurisdiction conflict detection
        conflict_map = self._conflicts.map(query)
        jurisdiction_conflicts = conflict_map.to_dict()["conflicts"]

        # ── 5. Persist ────────────────────────────────────────────────────────
        response_dict = {r.agent_id: r.answer for r in agent_responses}
        async with AsyncSessionFactory() as session:
            repo = QueryRepository(session)
            orm = QueryORM(id=query_id, user_query=query)
            orm.resolved_answer = consensus.merged_answer
            orm.consensus_score = consensus.consensus_score
            orm.decay_score = decay.score
            orm.set_conflict_flags([c["conflict_id"] for c in jurisdiction_conflicts])
            orm.set_citations(citation_dicts)
            orm.set_agent_responses(response_dict)
            await repo.create(orm)

        logger.info(
            "[%s] Done. consensus=%s score=%.2f decay=%.2f",
            query_id,
            consensus.consensus_reached,
            consensus.consensus_score,
            decay.score,
        )

        return OrchestratorResponse(
            query_id=query_id,
            query=query,
            answer=consensus.merged_answer,
            consensus_reached=consensus.consensus_reached,
            consensus_score=consensus.consensus_score,
            decay_score=decay.score,
            decay_label=decay.label,
            decay_warning=decay.warning,
            conflict_summary=consensus.conflict_summary,
            jurisdiction_conflicts=jurisdiction_conflicts,
            citations=citation_dicts,
            agent_responses=response_dict,
        )
