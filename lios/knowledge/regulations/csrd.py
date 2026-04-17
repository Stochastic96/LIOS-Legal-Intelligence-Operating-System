"""CSRD – Corporate Sustainability Reporting Directive structured data."""

from __future__ import annotations

NAME = "CSRD"
FULL_NAME = "Corporate Sustainability Reporting Directive"
DIRECTIVE_NUMBER = "2022/2464/EU"
effective_date = "2023-01-05"
last_updated = "2024-07-25"
review_note = (
    "Phased application underway: large PIEs (>500 employees) reported first in 2024. "
    "The European Commission's Omnibus simplification package (2025) may reduce scope "
    "for smaller companies — monitor for amendments before the 2025 reporting deadline."
)
jurisdictions = ["EU"]

applicable_from = {
    "large_companies": "2024-01-01",
    "listed_smes": "2026-01-01",
    "non_eu_companies": "2028-01-01",
}

thresholds = {
    "large_company": {
        "employees_gt": 500,
        "turnover_eur_gt": 40_000_000,
        "balance_sheet_eur_gt": 20_000_000,
        "note": "Must meet at least two of three criteria (or >500 employees alone for phase 1)",
    },
    "listed_sme": {
        "listed": True,
        "note": "Listed SMEs can opt out until 2028",
    },
    "non_eu_parent": {
        "turnover_eur_in_eu_gt": 150_000_000,
        "note": "Non-EU companies with substantial EU activity",
    },
}

articles = [
    {
        "id": "Art.1",
        "title": "Subject matter and scope",
        "text": (
            "This Directive amends Directive 2013/34/EU as regards the disclosure of "
            "non-financial and diversity information by certain large undertakings and groups. "
            "It introduces mandatory sustainability reporting requirements for large companies "
            "and listed SMEs operating in the EU."
        ),
        "topic": "scope",
    },
    {
        "id": "Art.2",
        "title": "Definitions",
        "text": (
            "For the purposes of this Directive: 'sustainability reporting' means reporting "
            "on sustainability matters including environmental, social and governance (ESG) factors. "
            "'Large undertaking' means an undertaking which exceeds the limits of at least two "
            "of three size criteria: net turnover > 40 million EUR, balance sheet > 20 million EUR, "
            "employees > 250 on average during the financial year."
        ),
        "topic": "definitions",
    },
    {
        "id": "Art.3",
        "title": "Sustainability reporting standards",
        "text": (
            "Member States shall require undertakings to include in the management report "
            "information necessary to understand the undertaking's impacts on sustainability matters "
            "and information necessary to understand how sustainability matters affect the undertaking. "
            "Sustainability reporting shall follow European Sustainability Reporting Standards (ESRS) "
            "adopted by the Commission."
        ),
        "topic": "reporting_standards",
    },
    {
        "id": "Art.4",
        "title": "Double materiality assessment",
        "text": (
            "Undertakings subject to this Directive shall conduct a double materiality assessment "
            "to identify which sustainability topics are material from both an impact perspective "
            "(actual and potential impacts of the company on the environment and society) and a "
            "financial materiality perspective (sustainability risks and opportunities that affect "
            "the company's financial performance)."
        ),
        "topic": "double_materiality",
    },
    {
        "id": "Art.5",
        "title": "Assurance of sustainability reporting",
        "text": (
            "Member States shall ensure that the sustainability information included in the "
            "management report is subject to assurance by an accredited independent auditor "
            "or certification body. Initially, limited assurance is required; the Commission "
            "may subsequently raise this to reasonable assurance by delegated act."
        ),
        "topic": "assurance",
    },
    {
        "id": "Art.6",
        "title": "Consolidated sustainability reporting",
        "text": (
            "A parent undertaking of a large group shall include sustainability information "
            "in its consolidated management report covering the parent and all subsidiaries "
            "included in the consolidated accounts. Subsidiary undertakings may be exempted "
            "from individual sustainability reporting if the parent's consolidated report "
            "covers the subsidiary."
        ),
        "topic": "consolidated_reporting",
    },
    {
        "id": "Art.7",
        "title": "Penalties",
        "text": (
            "Member States shall lay down rules on penalties applicable to infringements of "
            "national provisions adopted pursuant to this Directive and shall take all measures "
            "necessary to ensure that they are implemented. Penalties shall be effective, "
            "proportionate and dissuasive. Member States shall notify the Commission of those "
            "rules and measures by 6 July 2024."
        ),
        "topic": "penalties",
    },
    {
        "id": "Art.8",
        "title": "Supply chain due diligence",
        "text": (
            "Undertakings shall report on due diligence processes implemented with regard to "
            "sustainability matters, including the principal risks identified and how those risks "
            "are managed. This includes material impacts through the value chain, relationships "
            "with suppliers, and steps taken to prevent and mitigate adverse impacts."
        ),
        "topic": "supply_chain",
    },
    {
        "id": "Art.9",
        "title": "Digital taxonomy and machine-readable reporting",
        "text": (
            "Sustainability reporting shall be prepared in a digital format that is machine-readable "
            "using the European Single Electronic Format (ESEF). The information shall be tagged "
            "using the digital taxonomy specified in the Commission Delegated Regulation on ESEF, "
            "enabling automated processing and comparison across companies and jurisdictions."
        ),
        "topic": "digital_reporting",
    },
    {
        "id": "Art.10",
        "title": "Transition provisions and phased implementation",
        "text": (
            "The application of this Directive is phased: large public-interest entities with "
            ">500 employees apply from financial year 2024; other large undertakings from 2025; "
            "listed SMEs, small and non-complex credit institutions, and captive insurance "
            "undertakings from 2026 (with opt-out until 2028); non-EU parent undertakings from 2028."
        ),
        "topic": "timeline",
    },
    {
        "id": "Art.11",
        "title": "Third country equivalence",
        "text": (
            "The Commission may adopt implementing acts establishing that the sustainability "
            "reporting standards of a third country are equivalent to the European Sustainability "
            "Reporting Standards for the purpose of satisfying the reporting obligations of "
            "non-EU undertakings under this Directive."
        ),
        "topic": "third_country",
    },
]
