"""ESRS – European Sustainability Reporting Standards structured data."""

from __future__ import annotations

NAME = "ESRS"
FULL_NAME = "European Sustainability Reporting Standards"
REGULATION_NUMBER = "Commission Delegated Regulation (EU) 2023/2772"
effective_date = "2023-07-31"
last_updated = "2024-07-31"
review_note = (
    "ESRS Set 1 (12 cross-cutting and topical standards) was adopted July 2023. "
    "Sector-specific ESRS (Set 2) development is ongoing — expected adoption 2026. "
    "Proportionality provisions for SME-equivalent entities remain under review."
)
jurisdictions = ["EU"]

standards = {
    "ESRS_1": "General Requirements",
    "ESRS_2": "General Disclosures",
    "ESRS_E1": "Climate Change",
    "ESRS_E2": "Pollution",
    "ESRS_E3": "Water and Marine Resources",
    "ESRS_E4": "Biodiversity and Ecosystems",
    "ESRS_E5": "Resource Use and Circular Economy",
    "ESRS_S1": "Own Workforce",
    "ESRS_S2": "Workers in the Value Chain",
    "ESRS_S3": "Affected Communities",
    "ESRS_S4": "Consumers and End-users",
    "ESRS_G1": "Business Conduct",
}

articles = [
    {
        "id": "ESRS_1",
        "title": "General Requirements",
        "text": (
            "ESRS 1 sets out the general requirements for sustainability reporting under the CSRD. "
            "It establishes the architecture of the ESRS, the qualitative characteristics of "
            "information, the materiality assessment process (double materiality), the structure "
            "and elements of sustainability statements, and connectivity with financial reporting."
        ),
        "topic": "general_requirements",
        "standard": "ESRS_1",
    },
    {
        "id": "ESRS_2",
        "title": "General Disclosures",
        "text": (
            "ESRS 2 specifies general disclosures that all undertakings subject to CSRD must provide, "
            "regardless of their materiality assessment. These include: governance structures and "
            "processes for sustainability, strategy and business model, materiality assessment process, "
            "and metrics and targets related to material sustainability topics."
        ),
        "topic": "general_disclosures",
        "standard": "ESRS_2",
    },
    {
        "id": "ESRS_E1",
        "title": "Climate Change",
        "text": (
            "ESRS E1 addresses climate change. Undertakings shall disclose: transition plans for "
            "climate change mitigation, physical and transition climate risks, GHG emissions "
            "(Scope 1, 2, and 3), energy consumption, and targets aligned with limiting global "
            "warming to 1.5°C in line with the Paris Agreement. Gross GHG emissions must be "
            "reported in metric tons of CO2 equivalent."
        ),
        "topic": "climate",
        "standard": "ESRS_E1",
    },
    {
        "id": "ESRS_E2",
        "title": "Pollution",
        "text": (
            "ESRS E2 covers pollution of air, water, and soil. Undertakings shall disclose "
            "material pollution-related impacts, risks and opportunities, policies, actions, "
            "resources and targets related to pollution prevention and control. Key metrics "
            "include emissions to air (NOx, SOx, PM), releases to water, and hazardous waste."
        ),
        "topic": "pollution",
        "standard": "ESRS_E2",
    },
    {
        "id": "ESRS_E3",
        "title": "Water and Marine Resources",
        "text": (
            "ESRS E3 addresses water and marine resources. Disclosure requirements include "
            "water consumption, water withdrawal by source, water intensity, and impacts on "
            "marine ecosystems. Companies in water-stressed areas face enhanced disclosure "
            "obligations regarding water management practices and targets."
        ),
        "topic": "water",
        "standard": "ESRS_E3",
    },
    {
        "id": "ESRS_E4",
        "title": "Biodiversity and Ecosystems",
        "text": (
            "ESRS E4 requires undertakings to disclose their impacts and dependencies on "
            "biodiversity and ecosystems, including direct drivers of biodiversity loss "
            "(land use change, exploitation, climate change, pollution, invasive species). "
            "Companies must disclose sites located in or near biodiversity-sensitive areas "
            "and their biodiversity management plans."
        ),
        "topic": "biodiversity",
        "standard": "ESRS_E4",
    },
    {
        "id": "ESRS_S1",
        "title": "Own Workforce",
        "text": (
            "ESRS S1 covers the undertaking's own workforce. Required disclosures include: "
            "workforce composition (full-time, part-time, non-employee workers), health and "
            "safety metrics (injury rates, lost days), pay gap by gender, collective bargaining "
            "coverage, and social protection. Companies must also disclose policies on working "
            "conditions, equal treatment, and freedom of association."
        ),
        "topic": "workforce",
        "standard": "ESRS_S1",
    },
    {
        "id": "ESRS_S2",
        "title": "Workers in the Value Chain",
        "text": (
            "ESRS S2 addresses workers in the value chain beyond the undertaking's own employees. "
            "This includes upstream supply chain workers and downstream distribution workers. "
            "Undertakings shall disclose material impacts on value chain workers, due diligence "
            "processes, and remediation mechanisms. This standard is closely linked to CSRD "
            "supply chain due diligence requirements."
        ),
        "topic": "supply_chain_workers",
        "standard": "ESRS_S2",
    },
    {
        "id": "ESRS_G1",
        "title": "Business Conduct",
        "text": (
            "ESRS G1 covers governance, business ethics and corporate culture. Undertakings shall "
            "disclose: anti-corruption and anti-bribery policies and training, confirmed incidents "
            "of corruption or bribery, payment practices (especially regarding SMEs), political "
            "engagement and lobbying, and whistleblower protection mechanisms. The standard "
            "applies to all undertakings subject to CSRD."
        ),
        "topic": "governance",
        "standard": "ESRS_G1",
    },
    {
        "id": "ESRS_E5",
        "title": "Resource Use and Circular Economy",
        "text": (
            "ESRS E5 addresses resource use and the circular economy. Undertakings must disclose "
            "inflows and outflows of materials, waste generation and management, and measures "
            "taken to extend product life cycles. Key metrics include material consumption by "
            "type, recycled content, and waste diverted from disposal versus disposed."
        ),
        "topic": "circular_economy",
        "standard": "ESRS_E5",
    },
]
