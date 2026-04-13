"""Base agent definition with rule-based fallback."""

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
    """Abstract base for all LIOS specialist agents."""

    name: str = "base"
    domain: str = "general"
    # Subclasses declare which regulations they focus on
    primary_regulations: list[str] = []

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        self.db = db or RegulatoryDatabase()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze(self, query: str, context: dict[str, Any] | None = None) -> AgentResponse:
        """Main entry point.  Uses rule-based analysis; LLM optional."""
        context = context or {}
        return self._rule_based_analyze(query, context)

    # ------------------------------------------------------------------
    # Rule-based engine (subclasses may extend _domain_keywords / _score_relevance)
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
        # Also do a global search if no primary regulation results
        if not results:
            results = self.db.search_articles(query_lower)
        # Keep top 5
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:5]

    def _compose_answer(
        self, query_lower: str, articles: list[dict[str, Any]], context: dict[str, Any]
    ) -> tuple[str, list[str]]:
        """Produce a human-readable answer + key conclusion keywords."""
        if not articles:
            return (
                f"[{self.name}] Insufficient regulatory data found for this query "
                f"within the {self.domain} domain. Please consult the full regulatory text.",
                ["insufficient_data"],
            )

        top = articles[0]
        regulation = top["regulation"]
        article_id = top["article_id"]
        title = top.get("title", "")
        text = top.get("text", "")

        # Domain-specific preamble
        conclusion_kws = self._extract_conclusion_keywords(query_lower, articles)

        answer_lines = [
            f"[{self.name}] Based on {regulation} {article_id} ({title}):",
            "",
            text[:400] + ("..." if len(text) > 400 else ""),
            "",
        ]
        if len(articles) > 1:
            others = ", ".join(
                f"{a['regulation']} {a['article_id']}" for a in articles[1:3]
            )
            answer_lines.append(f"Additional relevant provisions: {others}.")

        answer_lines.extend(self._domain_analysis(query_lower, articles, context))

        return "\n".join(answer_lines), conclusion_kws

    @abstractmethod
    def _domain_analysis(
        self, query_lower: str, articles: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[str]:
        """Domain-specific analysis lines appended to the answer."""
        ...

    def _extract_conclusion_keywords(
        self, query_lower: str, articles: list[dict[str, Any]]
    ) -> list[str]:
        """Extract short conclusion keywords for consensus comparison."""
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
        # Clamp to [0.3, 0.95]
        return min(0.95, max(0.3, top_score * 0.15))

    def _build_reasoning(self, query_lower: str, articles: list[dict[str, Any]]) -> str:
        if not articles:
            return f"No relevant articles found in {self.primary_regulations} for this query."
        return (
            f"Agent '{self.name}' searched {self.primary_regulations} and found "
            f"{len(articles)} relevant article(s). "
            f"Top match: {articles[0]['regulation']} {articles[0]['article_id']} "
            f"(score={articles[0]['relevance_score']})."
        )
