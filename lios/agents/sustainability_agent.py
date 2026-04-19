"""Sustainability domain agent – CSRD, ESRS, EU Taxonomy focus."""

from __future__ import annotations

from lios.agents.base_agent import BaseAgent, DomainRule
from lios.knowledge.regulatory_db import RegulatoryDatabase


class SustainabilityAgent(BaseAgent):
    name = "sustainability_agent"
    domain = "sustainability"
    primary_regulations = ["CSRD", "ESRS", "EU_TAXONOMY"]

    DOMAIN_RULES = [
        DomainRule(
            keywords=["material", "double material", "impact", "materiality"],
            text=(
                "Note: CSRD Art.4 requires a double materiality assessment covering "
                "both impact materiality (company's effect on environment/society) and "
                "financial materiality (sustainability risks affecting the company)."
            ),
        ),
        DomainRule(
            keywords=["ghg", "greenhouse", "climate", "emission", "scope 1", "scope 2", "scope 3"],
            text=(
                "Under ESRS E1, companies must disclose Scope 1, 2, and 3 GHG emissions "
                "in tCO2e, alongside climate transition plans aligned with the Paris Agreement."
            ),
        ),
        DomainRule(
            keywords=["taxonomy", "green", "sustainable activit", "dnsh", "do no significant harm"],
            text=(
                "EU Taxonomy Art.3 requires activities to: (1) substantially contribute to "
                "an environmental objective, (2) do no significant harm (DNSH) to others, "
                "and (3) meet minimum social safeguards."
            ),
        ),
        DomainRule(
            keywords=["threshold", "appl", "scope", "size", "employee", "turnover"],
            text=(
                "CSRD applies to: (phase 1) public-interest entities >500 employees from FY2024; "
                "(phase 2) other large companies from FY2025; (phase 3) listed SMEs from FY2026."
            ),
        ),
        DomainRule(
            keywords=["assurance", "audit", "third-party", "verification"],
            text=(
                "CSRD Art.5 requires limited assurance of the sustainability statement from an "
                "accredited independent auditor or certification body. The Commission may raise "
                "this to reasonable assurance in future delegated acts."
            ),
        ),
        DomainRule(
            keywords=["esef", "xbrl", "digital", "machine-readable", "tagging"],
            text=(
                "Under CSRD Art.9, sustainability reporting must be prepared in ESEF (iXBRL) "
                "format using the sustainability reporting taxonomy, enabling automated data "
                "extraction and comparison across companies."
            ),
        ),
        DomainRule(
            keywords=["biodiversity", "ecosystem", "nature", "land use"],
            text=(
                "ESRS E4 (Biodiversity and Ecosystems) requires disclosure of material impacts, "
                "risks, and opportunities related to biodiversity loss, land use, water use, and "
                "ecosystem degradation, aligned with the Kunming-Montreal Global Biodiversity Framework."
            ),
        ),
        DomainRule(
            keywords=["water", "marine", "ocean", "freshwater"],
            text=(
                "ESRS E3 (Water and Marine Resources) requires companies to report on material "
                "water withdrawal, consumption, and discharge impacts, including water stress "
                "area assessments and targets to reduce water use."
            ),
        ),
        DomainRule(
            keywords=["circular", "waste", "resource", "recycl"],
            text=(
                "ESRS E5 (Resource Use and Circular Economy) requires disclosure of resource "
                "inflows and outflows, waste management practices, and transition plans toward "
                "a circular economy model."
            ),
        ),
        DomainRule(
            keywords=["social", "worker", "employee", "community", "human rights"],
            text=(
                "ESRS S1 (Own Workforce) requires disclosure of working conditions, equal "
                "treatment, diversity policies, and health & safety data for own employees. "
                "ESRS S3 covers affected communities; ESRS S4 covers consumers and end-users."
            ),
        ),
        DomainRule(
            keywords=["governance", "board", "ethics", "anti-corruption", "whistleblow"],
            text=(
                "ESRS G1 (Business Conduct) requires disclosure of anti-corruption and "
                "anti-bribery policies, whistleblower protection mechanisms, supplier "
                "payment practices, and corporate culture."
            ),
        ),
    ]

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        super().__init__(db)
