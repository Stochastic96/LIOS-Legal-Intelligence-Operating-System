"""Finance domain agent – SFDR, EU Taxonomy financial sector, disclosures."""

from __future__ import annotations

from typing import Any

from lios.agents.base_agent import BaseAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase


class FinanceAgent(BaseAgent):
    name = "finance_agent"
    domain = "finance"
    primary_regulations = ["SFDR", "EU_TAXONOMY"]

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        super().__init__(db)

    def _domain_analysis(
        self, query_lower: str, articles: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[str]:
        lines: list[str] = []

        # SFDR article classification
        if any(kw in query_lower for kw in ["article 6", "article 8", "article 9", "art.6", "art.8", "art.9", "fund", "esg fund"]):
            lines.append(
                "SFDR classifies financial products as: Article 6 (no sustainability claims), "
                "Article 8 (promotes ESG characteristics – 'light green'), or "
                "Article 9 (sustainable investment objective – 'dark green'). "
                "Each classification has distinct pre-contractual and periodic disclosure requirements."
            )

        # PAI – Principal Adverse Impact
        if any(kw in query_lower for kw in ["pai", "principal adverse", "adverse impact"]):
            lines.append(
                "SFDR Art.4 requires large financial market participants (>500 employees) to publish "
                "a PAI statement covering 14 mandatory indicators including GHG emissions, carbon "
                "footprint, biodiversity impacts, water emissions, and social violations."
            )

        # Taxonomy alignment for financial products
        if any(kw in query_lower for kw in ["taxonomy", "green", "taxonomy.aligned", "kpi"]):
            lines.append(
                "Financial products subject to SFDR must disclose taxonomy-aligned investment "
                "percentages as a proportion of turnover, CapEx, and OpEx KPIs. Art.8 products "
                "must disclose if any taxonomy-aligned investments are included; Art.9 products "
                "must disclose taxonomy-alignment percentage."
            )

        # Greenwashing / ESG claims
        if any(kw in query_lower for kw in ["greenwash", "esg claim", "mislead"]):
            lines.append(
                "SFDR does not directly define 'sustainable investment' in sufficient granularity, "
                "creating greenwashing risk. Regulators (ESMA, national NCAs) have increased "
                "scrutiny of Art.8/9 classifications. Firms must ensure disclosures are accurate, "
                "not misleading, and proportionate to actual ESG integration."
            )

        # Disclosure timelines
        if any(kw in query_lower for kw in ["disclos", "report", "when", "deadline", "timeline"]):
            lines.append(
                "SFDR Level 1 applied from 10 March 2021. SFDR RTS (Level 2) detailed disclosure "
                "templates applied from 1 January 2023. Periodic reports must follow SFDR Annex "
                "templates. The Commission is reviewing SFDR classification system (2024-2025)."
            )

        if not lines:
            lines.append(
                "Financial sector entities should consider SFDR disclosure obligations "
                "and EU Taxonomy alignment requirements for sustainable finance products."
            )

        return lines
