"""SFDR – Sustainable Finance Disclosure Regulation structured data."""

from __future__ import annotations

NAME = "SFDR"
FULL_NAME = "Sustainable Finance Disclosure Regulation"
REGULATION_NUMBER = "2019/2088/EU"
effective_date = "2021-03-10"
last_updated = "2024-04-22"
review_note = (
    "SFDR Level 2 Regulatory Technical Standards (RTS) applying from January 2023. "
    "The European Commission launched a targeted consultation on SFDR reform in 2023–2024; "
    "a revised framework (potentially replacing Art.8/9 labels) is expected 2025–2026."
)
jurisdictions = ["EU"]

fund_classifications = {
    "Article_6": {
        "label": "Article 6 – No sustainability claims",
        "description": (
            "Financial products that do not integrate sustainability risks in a systematic "
            "manner, or where sustainability risks are not relevant. Must include explanation "
            "of why sustainability risks are not relevant, or how sustainability risks are "
            "integrated and their likely impact on returns."
        ),
        "disclosure_requirements": [
            "Statement on integration of sustainability risks",
            "Explanation if sustainability risks are deemed not relevant",
        ],
    },
    "Article_8": {
        "label": "Article 8 – ESG Characteristics ('light green')",
        "description": (
            "Financial products that promote environmental or social characteristics, or a "
            "combination thereof, where the companies in which the investments are made follow "
            "good governance practices. Must disclose how these characteristics are met, "
            "what proportion of investments are sustainable, and index benchmarks used."
        ),
        "disclosure_requirements": [
            "Description of environmental or social characteristics",
            "Information on methodologies used to assess characteristics",
            "Good governance assessment criteria",
            "Proportion of sustainable investments (if any)",
            "Taxonomy-aligned investment percentage (if any)",
            "Pre-contractual and periodic disclosures",
        ],
    },
    "Article_9": {
        "label": "Article 9 – Sustainable investment objective ('dark green')",
        "description": (
            "Financial products that have a sustainable investment as their objective, "
            "or reduction in carbon emissions as their objective. Must disclose how the "
            "sustainable investment objective is attained, how the 'do no significant harm' "
            "principle is applied, and how principal adverse impacts are considered."
        ),
        "disclosure_requirements": [
            "Description of sustainable investment objective",
            "How sustainable investment objective is attained",
            "Do No Significant Harm (DNSH) statement",
            "Principal Adverse Impact (PAI) indicators",
            "Proportion of taxonomy-aligned investments",
            "Reference benchmark (if used)",
        ],
    },
}

principal_adverse_impact_indicators = [
    {"id": "PAI_1", "category": "climate", "indicator": "GHG emissions (Scope 1, 2, 3)"},
    {"id": "PAI_2", "category": "climate", "indicator": "Carbon footprint"},
    {"id": "PAI_3", "category": "climate", "indicator": "GHG intensity of investee companies"},
    {"id": "PAI_4", "category": "climate", "indicator": "Exposure to fossil fuel companies"},
    {"id": "PAI_5", "category": "climate", "indicator": "Share of non-renewable energy"},
    {"id": "PAI_6", "category": "environment", "indicator": "Energy consumption intensity"},
    {"id": "PAI_7", "category": "environment", "indicator": "Activities negatively affecting biodiversity"},
    {"id": "PAI_8", "category": "environment", "indicator": "Emissions to water"},
    {"id": "PAI_9", "category": "environment", "indicator": "Hazardous waste ratio"},
    {"id": "PAI_10", "category": "social", "indicator": "Violations of UNGP/OECD guidelines"},
    {"id": "PAI_11", "category": "social", "indicator": "Gender pay gap"},
    {"id": "PAI_12", "category": "social", "indicator": "Board gender diversity"},
    {"id": "PAI_13", "category": "social", "indicator": "Exposure to controversial weapons"},
]

articles = [
    {
        "id": "Art.2",
        "title": "Definitions",
        "text": (
            "'Sustainable investment' means an investment in an economic activity that contributes "
            "to an environmental or social objective, provided that the investment does not "
            "significantly harm any environmental or social objective, and that the investee "
            "companies follow good governance practices."
        ),
        "topic": "definitions",
    },
    {
        "id": "Art.4",
        "title": "Principal adverse impact disclosure",
        "text": (
            "Financial market participants shall publish and maintain on their websites a statement "
            "on due diligence policies with respect to the principal adverse impacts of investment "
            "decisions on sustainability factors. The statement shall include 64 mandatory indicators "
            "across climate, environment, social and governance dimensions."
        ),
        "topic": "pai_disclosure",
    },
    {
        "id": "Art.6",
        "title": "Sustainability risk integration",
        "text": (
            "Financial market participants shall include descriptions of: (a) how sustainability "
            "risks are integrated in investment decisions; and (b) the results of the assessment "
            "of the likely impacts of sustainability risks on the returns of financial products. "
            "Where sustainability risks are deemed not relevant, a clear and concise explanation "
            "of the reasons must be provided."
        ),
        "topic": "sustainability_risk",
    },
    {
        "id": "Art.8",
        "title": "Transparency of ESG financial products",
        "text": (
            "Where a financial product promotes, among other characteristics, environmental or "
            "social characteristics, or a combination of those characteristics, and where the "
            "companies in which the investments are made follow good governance practices, the "
            "information disclosed pre-contractually shall include: description of characteristics, "
            "index benchmark information, and where applicable taxonomy-alignment percentage."
        ),
        "topic": "article8_product",
    },
    {
        "id": "Art.9",
        "title": "Transparency of sustainable investments",
        "text": (
            "Where a financial product has sustainable investment as its objective and an index "
            "has been designated as a reference benchmark, the information disclosed shall include: "
            "description of how the designated index is aligned with the objective; explanation "
            "of why and how the designated index aligned with that objective differs from a "
            "broad market index; and where no index has been designated, explanation of how "
            "that objective is to be attained."
        ),
        "topic": "article9_product",
    },
    {
        "id": "Art.11",
        "title": "Periodic disclosure",
        "text": (
            "Financial market participants shall include in periodic reports: (a) for Art.8 "
            "products: description of environmental or social characteristics promoted; "
            "(b) for Art.9 products: description of the sustainable investment objective "
            "and the overall sustainability-related impact of the financial product through "
            "relevant sustainability indicators."
        ),
        "topic": "periodic_disclosure",
    },
]
