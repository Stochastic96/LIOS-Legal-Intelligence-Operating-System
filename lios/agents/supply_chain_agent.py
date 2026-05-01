"""Supply chain domain agent – CSRD supply chain, due diligence."""

from __future__ import annotations

from lios.agents.base_agent import BaseAgent, DomainRule
from lios.knowledge.regulatory_db import RegulatoryDatabase


class SupplyChainAgent(BaseAgent):
    name = "supply_chain_agent"
    domain = "supply_chain"
    primary_regulations = ["CSRD", "ESRS"]

    DOMAIN_RULES = [
        DomainRule(
            keywords=["supply chain", "supplier", "due diligence", "value chain"],
            text=(
                "CSRD Art.8 mandates disclosure of due diligence processes across the value chain, "
                "including upstream suppliers and downstream distributors. Companies must identify, "
                "prevent, and mitigate adverse sustainability impacts."
            ),
        ),
        DomainRule(
            keywords=["worker", "labour", "labor", "workforce", "human rights"],
            text=(
                "ESRS S2 (Workers in the Value Chain) requires disclosure of material impacts on "
                "value chain workers, including labour rights, health & safety, and fair wages. "
                "This links to OECD Guidelines and UN Guiding Principles on Business and Human Rights."
            ),
        ),
        DomainRule(
            keywords=["third-party", "third party", "non-eu", "global", "international"],
            text=(
                "For non-EU suppliers, the CSRD supply chain scope extends to material impacts "
                "in third countries. The EU Corporate Sustainability Due Diligence Directive (CS3D) "
                "complements CSRD with mandatory due diligence obligations."
            ),
        ),
        DomainRule(
            keywords=["report", "disclos", "data"],
            text=(
                "Supply chain data must be included in the CSRD sustainability statement. "
                "Where complete data from all tier-1 suppliers is unavailable, companies may "
                "use estimates based on sector averages with appropriate disclosure."
            ),
        ),
        DomainRule(
            keywords=["scope 3", "upstream", "downstream", "indirect emission"],
            text=(
                "Scope 3 GHG emissions from the supply chain (ESRS E1) must be disclosed when "
                "material. Companies should use supplier-specific data where available, with "
                "sector-average emission factors as a fallback. Scope 3 Category 1 (Purchased "
                "Goods & Services) is typically the largest source for manufacturing companies."
            ),
        ),
        DomainRule(
            keywords=["cs3d", "csddd", "corporate sustainability due diligence"],
            text=(
                "The EU Corporate Sustainability Due Diligence Directive (CS3D/CSDDD) introduces "
                "a mandatory human rights and environmental due diligence obligation for large "
                "companies (>1 000 employees, >450 M EUR turnover). It requires companies to "
                "identify, prevent, mitigate, and remediate adverse impacts throughout their chain "
                "of activities, with liability provisions and civil liability rules."
            ),
        ),
        DomainRule(
            keywords=["conflict mineral", "cobalt", "tin", "tantalum", "tungsten"],
            text=(
                "EU Conflict Minerals Regulation (2021/821) requires importers of tin, tantalum, "
                "tungsten, and gold (3TG) to conduct OECD-aligned supply chain due diligence. "
                "CSRD ESRS S2 disclosures should include conflict mineral sourcing risks."
            ),
        ),
    ]

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        super().__init__(db)
