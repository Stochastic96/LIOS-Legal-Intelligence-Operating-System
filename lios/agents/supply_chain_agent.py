"""Supply chain domain agent – CSRD supply chain, due diligence."""

from __future__ import annotations

from typing import Any

from lios.agents.base_agent import BaseAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase


class SupplyChainAgent(BaseAgent):
    name = "supply_chain_agent"
    domain = "supply_chain"
    primary_regulations = ["CSRD", "ESRS"]

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        super().__init__(db)

    def _domain_analysis(
        self, query_lower: str, articles: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[str]:
        lines: list[str] = []

        # Supply chain due diligence
        if any(kw in query_lower for kw in ["supply chain", "supplier", "due diligence", "value chain"]):
            lines.append(
                "CSRD Art.8 mandates disclosure of due diligence processes across the value chain, "
                "including upstream suppliers and downstream distributors. Companies must identify, "
                "prevent, and mitigate adverse sustainability impacts."
            )

        # ESRS S2 – workers in value chain
        if any(kw in query_lower for kw in ["worker", "labour", "labor", "workforce", "human rights"]):
            lines.append(
                "ESRS S2 (Workers in the Value Chain) requires disclosure of material impacts on "
                "value chain workers, including labour rights, health & safety, and fair wages. "
                "This links to OECD Guidelines and UN Guiding Principles on Business and Human Rights."
            )

        # Third-party / non-EU suppliers
        if any(kw in query_lower for kw in ["third.party", "non-eu", "global", "international"]):
            lines.append(
                "For non-EU suppliers, the CSRD supply chain scope extends to material impacts "
                "in third countries. The EU Corporate Sustainability Due Diligence Directive (CS3D) "
                "complements CSRD with mandatory due diligence obligations."
            )

        # Reporting obligations for supply chain data
        if any(kw in query_lower for kw in ["report", "disclos", "data"]):
            lines.append(
                "Supply chain data must be included in the CSRD sustainability statement. "
                "Where complete data from all tier-1 suppliers is unavailable, companies may "
                "use estimates based on sector averages with appropriate disclosure."
            )

        if not lines:
            lines.append(
                "Supply chain sustainability obligations under CSRD require identification of "
                "material impacts, risks, and opportunities across the full value chain."
            )

        return lines
