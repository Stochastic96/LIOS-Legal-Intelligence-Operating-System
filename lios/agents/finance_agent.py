"""Finance domain agent – SFDR, EU Taxonomy financial sector, disclosures."""

from __future__ import annotations

from lios.agents.base_agent import BaseAgent, DomainRule
from lios.knowledge.regulatory_db import RegulatoryDatabase


class FinanceAgent(BaseAgent):
    name = "finance_agent"
    domain = "finance"
    primary_regulations = ["SFDR", "EU_TAXONOMY"]

    DOMAIN_RULES = [
        DomainRule(
            keywords=["article 6", "article 8", "article 9", "art.6", "art.8", "art.9", "fund", "esg fund"],
            text=(
                "SFDR classifies financial products as: Article 6 (no sustainability claims), "
                "Article 8 (promotes ESG characteristics – 'light green'), or "
                "Article 9 (sustainable investment objective – 'dark green'). "
                "Each classification has distinct pre-contractual and periodic disclosure requirements."
            ),
        ),
        DomainRule(
            keywords=["pai", "principal adverse", "adverse impact"],
            text=(
                "SFDR Art.4 requires large financial market participants (>500 employees) to publish "
                "a PAI statement covering 14 mandatory indicators including GHG emissions, carbon "
                "footprint, biodiversity impacts, water emissions, and social violations."
            ),
        ),
        DomainRule(
            keywords=["taxonomy", "green", "taxonomy-aligned", "taxonomy aligned", "kpi"],
            text=(
                "Financial products subject to SFDR must disclose taxonomy-aligned investment "
                "percentages as a proportion of turnover, CapEx, and OpEx KPIs. Art.8 products "
                "must disclose if any taxonomy-aligned investments are included; Art.9 products "
                "must disclose taxonomy-alignment percentage."
            ),
        ),
        DomainRule(
            keywords=["greenwash", "esg claim", "mislead"],
            text=(
                "SFDR does not directly define 'sustainable investment' in sufficient granularity, "
                "creating greenwashing risk. Regulators (ESMA, national NCAs) have increased "
                "scrutiny of Art.8/9 classifications. Firms must ensure disclosures are accurate, "
                "not misleading, and proportionate to actual ESG integration."
            ),
        ),
        DomainRule(
            keywords=["disclos", "report", "when", "deadline", "timeline"],
            text=(
                "SFDR Level 1 applied from 10 March 2021. SFDR RTS (Level 2) detailed disclosure "
                "templates applied from 1 January 2023. Periodic reports must follow SFDR Annex "
                "templates. The Commission is reviewing SFDR classification system (2024-2025)."
            ),
        ),
        DomainRule(
            keywords=["remuneration", "variable pay", "bonus"],
            text=(
                "Financial market participants must integrate sustainability risks into their "
                "remuneration policies. SFDR Art.5 requires disclosure of how remuneration "
                "policies are consistent with the integration of sustainability risks."
            ),
        ),
        DomainRule(
            keywords=["rts", "regulatory technical standard", "level 2", "template"],
            text=(
                "SFDR Level 2 Regulatory Technical Standards (Commission Delegated Regulation "
                "2022/1288) specify standardised disclosure templates for pre-contractual, "
                "periodic, and website disclosures. These templates became mandatory on "
                "1 January 2023 for all Art.8 and Art.9 products."
            ),
        ),
    ]

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        super().__init__(db)
