"""Base agent definition with rule-based analysis and structured legal output."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from lios.knowledge.regulatory_db import RegulatoryDatabase


@dataclass
class AgentResponse:
    agent_name: str
    answer: str
    citations: list[dict[str, Any]]
    confidence: float  # 0.0 – 1.0
    reasoning: str
    conclusion_keywords: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base for all LIOS agents."""

    name: str = "base"
    domain: str = "general"
    primary_regulations: list[str] = []

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        self.db = db or RegulatoryDatabase()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze(self, query: str, context: dict[str, Any] | None = None) -> AgentResponse:
        context = context or {}
        return self._rule_based_analyze(query, context)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def _rule_based_analyze(self, query: str, context: dict[str, Any]) -> AgentResponse:
        query_lower = query.lower()
        relevant_articles = self._find_relevant_articles(query_lower)
        answer, conclusion_keywords = self._compose_answer(query_lower, relevant_articles, context)
        citations = self._build_citations(relevant_articles)
        confidence = self._estimate_confidence(relevant_articles)
        reasoning = self._build_reasoning(query_lower, relevant_articles)

        return AgentResponse(
            agent_name=self.name,
            answer=answer,
            citations=citations,
            confidence=confidence,
            reasoning=reasoning,
            conclusion_keywords=conclusion_keywords,
        )

    def _find_relevant_articles(self, query_lower: str) -> list[dict[str, Any]]:
        """Search the regulatory DB for articles relevant to this query."""
        results: list[dict[str, Any]] = []
        for reg in self.primary_regulations:
            hits = self.db.search_articles(query_lower, regulation=reg)
            results.extend(hits)
        if not results:
            results = self.db.search_articles(query_lower)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:5]

    def _compose_answer(
        self, query_lower: str, articles: list[dict[str, Any]], context: dict[str, Any]
    ) -> tuple[str, list[str]]:
        """Build a structured legal draft with retrieved articles + expert domain analysis."""
        conclusion_kws = self._extract_conclusion_keywords(query_lower, articles)

        parts: list[str] = []

        # ── Legal sources retrieved from the regulatory database ──────────────
        if articles:
            source_blocks: list[str] = []
            for a in articles[:3]:
                reg = a["regulation"]
                art = a["article_id"]
                title = a.get("title", "")
                text = a.get("text", "")
                snippet = text[:700] + ("…" if len(text) > 700 else "")
                header = f"**{reg} {art}**" + (f" — {title}" if title else "")
                source_blocks.append(f"{header}\n{snippet}")
            parts.append("## Retrieved Legal Provisions\n\n" + "\n\n".join(source_blocks))

        # ── Expert domain analysis (keyword-triggered rule blocks) ────────────
        domain_lines = self._domain_analysis(query_lower, articles, context)
        if domain_lines:
            parts.append("## Compliance Analysis\n\n" + "\n\n".join(domain_lines))

        if not parts:
            return (
                "No specific regulatory provisions found for this query. "
                "Please consult the official CSRD, ESRS, EU Taxonomy, SFDR, or CS3D texts directly.",
                ["insufficient_data"],
            )

        return "\n\n---\n\n".join(parts), conclusion_kws

    @abstractmethod
    def _domain_analysis(
        self, query_lower: str, articles: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[str]:
        """Domain-specific expert analysis blocks appended to the answer."""
        ...

    # ------------------------------------------------------------------
    # Supporting helpers
    # ------------------------------------------------------------------

    def _extract_conclusion_keywords(
        self, query_lower: str, articles: list[dict[str, Any]]
    ) -> list[str]:
        keywords: list[str] = []
        applies_pattern = re.compile(
            r"\b(appl|mandator|requir|oblig|must|shall|compli|report)\w*\b"
        )
        exempt_pattern = re.compile(r"\b(exempt|not appl|not requir|exclud|opt.out)\w*\b")

        combined = query_lower + " " + " ".join(a.get("text", "") for a in articles[:2])
        if applies_pattern.search(combined):
            keywords.append("applies")
        if exempt_pattern.search(combined):
            keywords.append("exemption_possible")
        if not keywords:
            keywords.append("general_guidance")
        return keywords

    def _build_citations(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "regulation": a["regulation"],
                "article_id": a["article_id"],
                "title": a.get("title", ""),
                "relevance_score": a["relevance_score"],
            }
            for a in articles
        ]

    def _estimate_confidence(self, articles: list[dict[str, Any]]) -> float:
        if not articles:
            return 0.2
        top_score = articles[0]["relevance_score"]
        return min(0.95, max(0.3, top_score))

    def _build_reasoning(self, query_lower: str, articles: list[dict[str, Any]]) -> str:
        if not articles:
            return f"No relevant articles found in {self.primary_regulations} for this query."
        return (
            f"Searched {self.primary_regulations}, found {len(articles)} relevant article(s). "
            f"Top match: {articles[0]['regulation']} {articles[0]['article_id']} "
            f"(score={articles[0]['relevance_score']})."
        )
