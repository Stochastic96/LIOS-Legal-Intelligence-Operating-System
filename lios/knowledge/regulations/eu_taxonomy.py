"""EU Taxonomy Regulation structured data."""

from __future__ import annotations

NAME = "EU_TAXONOMY"
FULL_NAME = "EU Taxonomy Regulation"
REGULATION_NUMBER = "2020/852/EU"
effective_date = "2020-06-22"
last_updated = "2022-01-01"
jurisdictions = ["EU"]

environmental_objectives = [
    {
        "id": "EO1",
        "title": "Climate change mitigation",
        "description": (
            "An economic activity substantially contributes to climate change mitigation where "
            "that activity contributes substantially to the stabilisation of greenhouse gas "
            "concentrations in the atmosphere at a level which prevents dangerous anthropogenic "
            "interference with the climate system, consistent with the long-term temperature goal "
            "of the Paris Agreement."
        ),
    },
    {
        "id": "EO2",
        "title": "Climate change adaptation",
        "description": (
            "An economic activity substantially contributes to climate change adaptation where "
            "that activity includes either: adaptation solutions that substantially reduce the "
            "risk of the adverse impact of the current climate and the expected future climate "
            "on that economic activity; or adaptation solutions that substantially reduce the "
            "adverse impact of the current climate and the expected future climate on people, "
            "nature or assets."
        ),
    },
    {
        "id": "EO3",
        "title": "Sustainable use and protection of water and marine resources",
        "description": (
            "An economic activity substantially contributes to the sustainable use and protection "
            "of water and marine resources where that activity contributes substantially to the "
            "good status of water bodies, including surface water and groundwater, or to preventing "
            "deterioration of water bodies that are already in good status."
        ),
    },
    {
        "id": "EO4",
        "title": "Transition to a circular economy",
        "description": (
            "An economic activity substantially contributes to the transition to a circular economy "
            "including waste prevention, re-use and recycling, where that activity contributes "
            "substantially to: waste prevention, re-use, repair or refurbishment, or increased use "
            "of secondary raw materials; or reduction in the use of primary raw materials."
        ),
    },
    {
        "id": "EO5",
        "title": "Pollution prevention and control",
        "description": (
            "An economic activity substantially contributes to pollution prevention and control "
            "where that activity contributes substantially to: prevention or reduction of pollutant "
            "emissions into air, water or land (other than GHGs); or improving the level of "
            "activities to deal with pollution."
        ),
    },
    {
        "id": "EO6",
        "title": "Protection and restoration of biodiversity and ecosystems",
        "description": (
            "An economic activity substantially contributes to the protection and restoration of "
            "biodiversity and ecosystems where that activity contributes substantially to: protecting, "
            "conserving or restoring biodiversity; or achieving the good condition of ecosystems, "
            "or protecting ecosystems that are already in good condition."
        ),
    },
]

articles = [
    {
        "id": "Art.3",
        "title": "Criteria for environmentally sustainable economic activities",
        "text": (
            "An economic activity shall qualify as environmentally sustainable where that activity: "
            "(a) contributes substantially to one or more of the environmental objectives; "
            "(b) does not significantly harm any of the environmental objectives (DNSH); "
            "(c) is carried out in compliance with minimum social safeguards; "
            "(d) complies with technical screening criteria established by the Commission."
        ),
        "topic": "taxonomy_criteria",
    },
    {
        "id": "Art.9",
        "title": "Environmental objectives",
        "text": (
            "For the purposes of establishing the degree to which an investment is environmentally "
            "sustainable, the environmental objectives are: (1) climate change mitigation; "
            "(2) climate change adaptation; (3) sustainable use and protection of water and marine "
            "resources; (4) transition to a circular economy; (5) pollution prevention and control; "
            "(6) protection and restoration of biodiversity and ecosystems."
        ),
        "topic": "environmental_objectives",
    },
    {
        "id": "Art.10",
        "title": "Substantial contribution to climate change mitigation",
        "text": (
            "An economic activity substantially contributes to climate change mitigation where "
            "the activity avoids or reduces greenhouse gas emissions, or removes GHGs from the "
            "atmosphere. Activities include renewable energy generation, energy efficient "
            "buildings, clean transport, and carbon capture and storage."
        ),
        "topic": "climate_mitigation",
    },
    {
        "id": "Art.17",
        "title": "Do No Significant Harm (DNSH)",
        "text": (
            "An economic activity does no significant harm to: (a) climate change mitigation if "
            "it does not lead to significant GHG emissions; (b) climate change adaptation if it "
            "does not significantly impede the adaptation of people, nature or assets; "
            "(c) sustainable use of water if it does not significantly detract from the good "
            "status of water bodies; (d) circular economy if it leads to significant "
            "inefficiencies in use of materials; (e) pollution prevention if it leads to "
            "significant increase of emissions into air, water or land; (f) biodiversity if "
            "it is significantly detrimental to the good condition of ecosystems."
        ),
        "topic": "dnsh",
    },
    {
        "id": "Art.18",
        "title": "Minimum social safeguards",
        "text": (
            "Minimum social safeguards refer to procedures implemented by an undertaking to "
            "ensure alignment with the OECD Guidelines for Multinational Enterprises and the "
            "UN Guiding Principles on Business and Human Rights, including the principles and "
            "rights set out in the core conventions of the International Labour Organisation."
        ),
        "topic": "social_safeguards",
    },
    {
        "id": "Art.8",
        "title": "Taxonomy disclosure obligations",
        "text": (
            "Financial market participants, large public interest entities, and non-financial "
            "undertakings subject to NFRD/CSRD shall disclose how and to what extent their "
            "activities are associated with environmentally sustainable economic activities. "
            "Key performance indicators include: taxonomy-eligible activities as proportion "
            "of turnover, capex, and opex."
        ),
        "topic": "disclosure",
    },
]

technical_screening_criteria = {
    "description": (
        "Technical screening criteria specify: (1) quantitative or qualitative thresholds "
        "that determine substantial contribution to each environmental objective; "
        "(2) indicators to assess DNSH; and (3) minimum social safeguards requirements. "
        "Criteria are set by Commission Delegated Regulations."
    ),
    "key_metrics": [
        "GHG emissions intensity (tCO2e per unit output)",
        "Energy performance (kWh/m2 for buildings)",
        "Renewable energy share (%)",
        "Waste recycling rate (%)",
        "Water consumption (m3 per unit)",
    ],
}
