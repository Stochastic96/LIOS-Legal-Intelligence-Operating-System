"""Sustainability domain agent – CSRD, ESRS, EU Taxonomy focus."""

from __future__ import annotations

from typing import Any

from lios.agents.base_agent import BaseAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase


class SustainabilityAgent(BaseAgent):
    name = "sustainability_agent"
    domain = "sustainability"
    primary_regulations = ["CSRD", "ESRS", "EU_TAXONOMY"]

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        super().__init__(db)

    def _domain_analysis(
        self, query_lower: str, articles: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[str]:
        lines: list[str] = []

        # Check for double materiality questions
        if any(kw in query_lower for kw in ["material", "double material", "impact"]):
            lines.append(
                "Note: CSRD Art.4 requires a double materiality assessment covering "
                "both impact materiality (company's effect on environment/society) and "
                "financial materiality (sustainability risks affecting the company)."
            )

        # Climate/GHG questions
        if any(kw in query_lower for kw in ["ghg", "greenhouse", "climate", "emission", "scope"]):
            lines.append(
                "Under ESRS E1, companies must disclose Scope 1, 2, and 3 GHG emissions "
                "in tCO2e, alongside climate transition plans aligned with the Paris Agreement."
            )

        # Taxonomy questions
        if any(kw in query_lower for kw in ["taxonomy", "green", "sustainable activit", "dnsh"]):
            lines.append(
                "EU Taxonomy Art.3 requires activities to: (1) substantially contribute to "
                "an environmental objective, (2) do no significant harm (DNSH) to others, "
                "and (3) meet minimum social safeguards."
            )

        # Reporting threshold questions
        if any(kw in query_lower for kw in ["threshold", "appl", "scope", "size", "employee", "turnover"]):
            lines.append(
                "CSRD applies to: (phase 1) public-interest entities >500 employees from FY2024; "
                "(phase 2) other large companies from FY2025; (phase 3) listed SMEs from FY2026."
            )

        if not lines:
            lines.append(
                "Consult CSRD, ESRS, and EU Taxonomy provisions for comprehensive "
                "sustainability reporting obligations."
            )

        return lines
