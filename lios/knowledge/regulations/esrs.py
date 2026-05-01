"""ESRS – European Sustainability Reporting Standards structured data."""

from __future__ import annotations

NAME = "ESRS"
FULL_NAME = "European Sustainability Reporting Standards"
REGULATION_NUMBER = "Commission Delegated Regulation (EU) 2023/2772"
effective_date = "2023-07-31"
last_updated = "2023-07-31"
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
        "keywords": ["general requirements", "architecture", "qualitative", "connectivity", "materiality", "reporting"],
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
        "keywords": ["general disclosures", "governance", "strategy", "business model", "material topics", "targets", "metrics"],
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
        "keywords": [
            "climate", "GHG", "greenhouse gas", "Scope 1", "Scope 2", "Scope 3",
            "Paris Agreement", "transition plan", "carbon", "emission", "net zero",
            "CO2", "decarbonisation", "climate risk", "physical risk", "transition risk",
        ],
        "text": (
            "ESRS E1 addresses climate change. Undertakings shall disclose: transition plans for "
            "climate change mitigation, physical and transition climate risks, GHG emissions "
            "(Scope 1, 2, and 3), energy consumption, and targets aligned with limiting global "
            "warming to 1.5°C in line with the Paris Agreement. Gross GHG emissions must be "
            "reported in metric tons of CO2 equivalent. Companies with significant Scope 3 "
            "emissions shall disclose Category 1-15 upstream and downstream Scope 3 emissions."
        ),
        "topic": "climate",
        "standard": "ESRS_E1",
    },
    {
        "id": "ESRS_E2",
        "title": "Pollution",
        "keywords": [
            "pollution", "air", "water", "soil", "NOx", "SOx", "particulate matter",
            "hazardous", "chemical", "emissions to air", "REACH", "persistent organic",
        ],
        "text": (
            "ESRS E2 covers pollution of air, water, and soil. Undertakings shall disclose "
            "material pollution-related impacts, risks and opportunities, policies, actions, "
            "resources and targets related to pollution prevention and control. Key metrics "
            "include emissions to air (NOx, SOx, PM), releases to water, and hazardous waste. "
            "Companies subject to the European Pollutant Release and Transfer Register (E-PRTR) "
            "must reference their registered pollutant releases."
        ),
        "topic": "pollution",
        "standard": "ESRS_E2",
    },
    {
        "id": "ESRS_E3",
        "title": "Water and Marine Resources",
        "keywords": [
            "water", "marine", "ocean", "freshwater", "withdrawal", "consumption",
            "water stress", "sea", "coastal", "groundwater", "surface water",
        ],
        "text": (
            "ESRS E3 addresses water and marine resources. Disclosure requirements include "
            "water consumption, water withdrawal by source, water intensity, and impacts on "
            "marine ecosystems. Companies in water-stressed areas face enhanced disclosure "
            "obligations regarding water management practices and targets. Undertakings must "
            "identify sites with material water-related impacts and disclose water recycling rates."
        ),
        "topic": "water",
        "standard": "ESRS_E3",
    },
    {
        "id": "ESRS_E4",
        "title": "Biodiversity and Ecosystems",
        "keywords": [
            "biodiversity", "ecosystem", "nature", "land use", "habitat", "species",
            "deforestation", "invasive", "Kunming-Montreal", "TNFD", "protected area",
        ],
        "text": (
            "ESRS E4 requires undertakings to disclose their impacts and dependencies on "
            "biodiversity and ecosystems, including direct drivers of biodiversity loss "
            "(land use change, exploitation, climate change, pollution, invasive species). "
            "Companies must disclose sites located in or near biodiversity-sensitive areas "
            "and their biodiversity management plans. Biodiversity transition plans must be "
            "aligned with the Kunming-Montreal Global Biodiversity Framework targets."
        ),
        "topic": "biodiversity",
        "standard": "ESRS_E4",
    },
    {
        "id": "ESRS_E5",
        "title": "Resource Use and Circular Economy",
        "keywords": [
            "circular economy", "waste", "resource", "recycl", "material", "reuse",
            "product lifecycle", "repair", "refurbish", "single-use plastic",
        ],
        "text": (
            "ESRS E5 addresses resource use and the circular economy. Undertakings must disclose "
            "inflows and outflows of materials, waste generation and management, and measures "
            "taken to extend product life cycles. Key metrics include material consumption by "
            "type, recycled content, and waste diverted from disposal versus disposed. "
            "Companies must align disclosures with the EU Circular Economy Action Plan."
        ),
        "topic": "circular_economy",
        "standard": "ESRS_E5",
    },
    {
        "id": "ESRS_S1",
        "title": "Own Workforce",
        "keywords": [
            "own workforce", "employee", "worker", "gender pay gap", "health safety",
            "injury rate", "collective bargaining", "social protection", "equal treatment",
            "diversity", "inclusion", "turnover rate", "training", "working conditions",
        ],
        "text": (
            "ESRS S1 covers the undertaking's own workforce. Required disclosures include: "
            "workforce composition (full-time, part-time, non-employee workers), health and "
            "safety metrics (injury rates, lost days), pay gap by gender, collective bargaining "
            "coverage, and social protection. Companies must also disclose policies on working "
            "conditions, equal treatment, and freedom of association. The gender pay gap metric "
            "must be disclosed as the difference in average gross hourly pay between men and women."
        ),
        "topic": "workforce",
        "standard": "ESRS_S1",
    },
    {
        "id": "ESRS_S2",
        "title": "Workers in the Value Chain",
        "keywords": [
            "value chain workers", "supply chain worker", "supplier", "labour rights",
            "human rights", "OECD Guidelines", "UN Guiding Principles", "UNGP",
            "child labour", "forced labour", "modern slavery",
        ],
        "text": (
            "ESRS S2 addresses workers in the value chain beyond the undertaking's own employees. "
            "This includes upstream supply chain workers and downstream distribution workers. "
            "Undertakings shall disclose material impacts on value chain workers, due diligence "
            "processes, and remediation mechanisms. This standard is closely linked to CSRD "
            "supply chain due diligence requirements and references the OECD Due Diligence "
            "Guidance for Responsible Business Conduct."
        ),
        "topic": "supply_chain_workers",
        "standard": "ESRS_S2",
    },
    {
        "id": "ESRS_S3",
        "title": "Affected Communities",
        "keywords": [
            "community", "indigenous", "local population", "land rights", "grievance",
            "social impact", "community engagement", "resettlement", "free prior informed consent",
        ],
        "text": (
            "ESRS S3 covers the undertaking's impacts on affected communities. Undertakings shall "
            "disclose material impacts on communities living in areas affected by the company's "
            "operations or value chain, including indigenous peoples. Disclosures must cover "
            "the approach to community engagement, grievance mechanisms, and how adverse impacts "
            "on communities are identified, prevented, mitigated, and remediated."
        ),
        "topic": "communities",
        "standard": "ESRS_S3",
    },
    {
        "id": "ESRS_S4",
        "title": "Consumers and End-users",
        "keywords": [
            "consumer", "end-user", "customer", "product safety", "data privacy",
            "responsible marketing", "vulnerable consumer", "product liability",
        ],
        "text": (
            "ESRS S4 addresses the undertaking's impacts on consumers and end-users. Companies "
            "shall disclose material impacts on consumers related to product safety, privacy, "
            "responsible marketing, and access to products and services. Key disclosures include "
            "data privacy practices, product recall incidents, and marketing ethics policies. "
            "Particular attention is required for impacts on vulnerable consumer groups."
        ),
        "topic": "consumers",
        "standard": "ESRS_S4",
    },
    {
        "id": "ESRS_G1",
        "title": "Business Conduct",
        "keywords": [
            "governance", "ethics", "anti-corruption", "anti-bribery", "whistleblower",
            "payment practices", "political lobbying", "corporate culture", "fraud",
            "bribery", "corruption incident",
        ],
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
]
