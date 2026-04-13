"""Legal Breakdown Generator – structured breakdown of regulatory topics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lios.knowledge.regulatory_db import RegulatoryDatabase


@dataclass
class LegalBreakdown:
    topic: str
    regulation: str
    summary: str
    key_articles: list[dict[str, Any]]
    obligations: list[str]
    penalties: list[str]
    timeline: list[dict[str, str]]


# Penalty information per regulation
_PENALTIES: dict[str, list[str]] = {
    "CSRD": [
        "Member States set their own penalties; must be effective, proportionate, dissuasive (Art.7).",
        "Germany: fines up to EUR 10 million or 5% of annual turnover for false non-financial statements.",
        "France: criminal liability for directors for deliberate misreporting.",
        "Potential liability for auditors providing incorrect assurance opinions.",
        "Reputational damage and investor sanctions for non-compliant companies.",
    ],
    "ESRS": [
        "Penalties enforced under CSRD framework (ESRS violations = CSRD violations).",
        "Incorrect or misleading ESRS disclosures may attract regulatory scrutiny from NCAs.",
        "Auditor sanctions for incorrect limited assurance on sustainability statements.",
    ],
    "EU_TAXONOMY": [
        "No specific EU-level penalties defined; enforcement via CSRD/NFRD penalty regimes.",
        "Misleading taxonomy alignment claims may constitute market abuse or greenwashing.",
        "ESMA and national NCAs may investigate misleading taxonomy disclosures.",
        "Potential civil liability to investors for material misstatements in EU Taxonomy KPIs.",
    ],
    "SFDR": [
        "Member States set SFDR penalties; coordination via ESMA.",
        "NCAs can require product reclassification (e.g., from Art.9 to Art.8).",
        "FCA (UK) and EU NCAs have taken enforcement actions for misleading ESG disclosures.",
        "AMF (France) fines for non-compliant sustainability disclosures in fund documentation.",
        "Potential greenwashing liability under consumer protection and MiFID II rules.",
    ],
}

# Timeline information per regulation
_TIMELINES: dict[str, list[dict[str, str]]] = {
    "CSRD": [
        {"date": "2023-01-05", "event": "CSRD entered into force"},
        {"date": "2024-07-06", "event": "Member States must transpose CSRD into national law"},
        {"date": "2024-01-01", "event": "Phase 1: PIEs with >500 employees (FY2024)"},
        {"date": "2025-01-01", "event": "Phase 2: All large companies (FY2025)"},
        {"date": "2026-01-01", "event": "Phase 3: Listed SMEs (FY2026, opt-out to 2028)"},
        {"date": "2028-01-01", "event": "Phase 4: Non-EU companies with EU turnover >150M EUR"},
    ],
    "ESRS": [
        {"date": "2023-07-31", "event": "ESRS Set 1 (Delegated Regulation 2023/2772) published"},
        {"date": "2024-01-01", "event": "ESRS applicable for FY2024 reports (Phase 1 companies)"},
        {"date": "2024-Q4", "event": "Expected: Sector-specific ESRS standards consultation"},
        {"date": "2026-Q4", "event": "Expected: Proportionate ESRS standards for listed SMEs"},
    ],
    "EU_TAXONOMY": [
        {"date": "2020-06-22", "event": "EU Taxonomy Regulation entered into force"},
        {"date": "2022-01-01", "event": "Climate Delegated Act (EO1 & EO2) applies"},
        {"date": "2023-01-01", "event": "Environmental Delegated Act (EO3-EO6) applies"},
        {"date": "2024-01-01", "event": "Full taxonomy KPI disclosure for large companies"},
    ],
    "SFDR": [
        {"date": "2021-03-10", "event": "SFDR Level 1 entered into application"},
        {"date": "2022-01-01", "event": "SFDR RTS (Level 2) enters into application"},
        {"date": "2023-01-01", "event": "Full RTS disclosure templates mandatory"},
        {"date": "2023-06-30", "event": "First PAI statements published (reference period 2022)"},
        {"date": "2024-2025", "event": "SFDR review by European Commission (potential reform)"},
    ],
}


class LegalBreakdownGenerator:
    """Generate structured legal breakdowns for topics within a regulation."""

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        self.db = db or RegulatoryDatabase()

    def generate_breakdown(self, topic: str, regulation: str) -> LegalBreakdown:
        reg_key = self._resolve_reg_key(regulation)
        reg = self.db.get_regulation(reg_key)

        if reg is None:
            return LegalBreakdown(
                topic=topic,
                regulation=regulation,
                summary=(
                    f"Regulation '{regulation}' not found in LIOS knowledge base. "
                    "Valid regulation names are: CSRD, ESRS, EU_TAXONOMY, SFDR."
                ),
                key_articles=[],
                obligations=[],
                penalties=[],
                timeline=[],
            )

        # Find relevant articles for the topic
        articles = self.db.search_articles(topic, regulation=reg_key)
        key_articles = [
            {
                "article_id": a["article_id"],
                "title": a["title"],
                "excerpt": a["text"][:250] + "..." if len(a["text"]) > 250 else a["text"],
                "relevance_score": a["relevance_score"],
            }
            for a in articles[:5]
        ]

        obligations = self._extract_obligations(topic, reg_key, articles)
        penalties = _PENALTIES.get(reg_key, ["See national transposition law for penalty details."])
        timeline = _TIMELINES.get(reg_key, [])
        summary = self._build_summary(topic, reg_key, reg, articles)

        return LegalBreakdown(
            topic=topic,
            regulation=reg_key,
            summary=summary,
            key_articles=key_articles,
            obligations=obligations,
            penalties=penalties,
            timeline=timeline,
        )

    def _extract_obligations(
        self,
        topic: str,
        reg_key: str,
        articles: list[dict[str, Any]],
    ) -> list[str]:
        """Extract obligation statements from matching articles."""
        obligations: list[str] = []
        obligation_starters = ("shall", "must", "required to", "obliged to", "have to")

        for article in articles[:3]:
            text = article.get("text", "")
            sentences = text.replace(";", ".").split(".")
            for sentence in sentences:
                s = sentence.strip()
                if any(s.lower().startswith(st) or f" {st} " in s.lower() for st in obligation_starters):
                    if len(s) > 20:
                        obligations.append(f"[{article['article_id']}] {s}.")

        if not obligations:
            obligations.append(
                f"Consult {reg_key} articles directly for specific obligations related to '{topic}'."
            )
        return obligations[:8]

    def _build_summary(
        self,
        topic: str,
        reg_key: str,
        reg: dict[str, Any],
        articles: list[dict[str, Any]],
    ) -> str:
        full_name = reg.get("full_name", reg_key)
        if not articles:
            return f"No specific provisions found in {full_name} for topic '{topic}'."
        top = articles[0]
        return (
            f"{full_name} addresses '{topic}' primarily through {top['article_id']} "
            f"({top['title']}). "
            f"{len(articles)} relevant provision(s) identified. "
            f"The regulation has been in effect since {reg.get('effective_date', 'N/A')} "
            f"and was last updated {reg.get('last_updated', 'N/A')}."
        )

    def _resolve_reg_key(self, regulation: str) -> str:
        mapping = {
            "csrd": "CSRD",
            "esrs": "ESRS",
            "eu taxonomy": "EU_TAXONOMY",
            "eu_taxonomy": "EU_TAXONOMY",
            "taxonomy": "EU_TAXONOMY",
            "sfdr": "SFDR",
        }
        return mapping.get(regulation.lower().strip(), regulation.upper())
