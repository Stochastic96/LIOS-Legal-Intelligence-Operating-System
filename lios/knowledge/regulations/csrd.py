"""CSRD – Corporate Sustainability Reporting Directive structured data."""

from __future__ import annotations

NAME = "CSRD"
FULL_NAME = "Corporate Sustainability Reporting Directive"
DIRECTIVE_NUMBER = "2022/2464/EU"
effective_date = "2023-01-05"
last_updated = "2023-01-05"
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
        "keywords": ["scope", "subject matter", "large undertaking", "SME", "applicability", "applies"],
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
        "keywords": ["definition", "large undertaking", "sustainability reporting", "turnover", "employees", "balance sheet"],
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
        "keywords": ["reporting standards", "ESRS", "management report", "sustainability statement", "mandatory"],
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
        "keywords": ["double materiality", "impact materiality", "financial materiality", "materiality assessment", "ESG"],
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
        "keywords": ["assurance", "audit", "auditor", "limited assurance", "reasonable assurance", "verification", "third-party"],
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
        "keywords": ["consolidated", "group", "parent", "subsidiary", "exemption", "group reporting"],
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
        "keywords": ["penalty", "sanction", "enforcement", "fine", "dissuasive", "non-compliance"],
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
        "keywords": ["supply chain", "due diligence", "value chain", "supplier", "upstream", "downstream", "adverse impact"],
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
        "keywords": ["ESEF", "XBRL", "iXBRL", "digital", "machine-readable", "electronic format", "tagging", "taxonomy"],
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
        "keywords": ["phased", "timeline", "implementation", "transition", "FY2024", "FY2025", "FY2026", "FY2028", "deadline"],
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
        "keywords": ["third country", "equivalence", "non-EU", "international", "equivalent standards"],
        "text": (
            "The Commission may adopt implementing acts establishing that the sustainability "
            "reporting standards of a third country are equivalent to the European Sustainability "
            "Reporting Standards for the purpose of satisfying the reporting obligations of "
            "non-EU undertakings under this Directive."
        ),
        "topic": "third_country",
    },
    {
        "id": "Art.12",
        "title": "Governance and oversight of sustainability",
        "keywords": ["governance", "board", "oversight", "management board", "supervisory board", "sustainability governance"],
        "text": (
            "The administrative, management and supervisory bodies of large undertakings are "
            "collectively responsible for ensuring that the sustainability statement is prepared "
            "and published in accordance with this Directive. The governing bodies shall have "
            "knowledge and skills in sustainability matters, or have access to expertise in "
            "those matters, to fulfil their responsibilities."
        ),
        "topic": "governance",
    },
    {
        "id": "Art.13",
        "title": "Sector-specific standards",
        "keywords": ["sector", "sector-specific", "industry", "sector standard", "ESRS sector"],
        "text": (
            "The Commission is empowered to adopt delegated acts to supplement this Directive "
            "by establishing sector-specific European Sustainability Reporting Standards. "
            "Sector-specific standards shall specify the sustainability topics that are "
            "presumed to be material for each sector, in addition to the cross-cutting "
            "disclosures required by general ESRS standards."
        ),
        "topic": "sector_standards",
    },
    {
        "id": "Art.14",
        "title": "SME proportionate reporting",
        "keywords": ["SME", "small", "medium", "proportionate", "voluntary", "listed SME", "opt-out"],
        "text": (
            "The Commission shall adopt delegated acts to establish proportionate sustainability "
            "reporting standards for listed SMEs, taking into account the capacity of SMEs and "
            "proportionality principles. Listed SMEs may opt out of the CSRD reporting obligation "
            "until financial years beginning 1 January 2028. Large non-listed SMEs in supply "
            "chains may face value chain reporting requests from large undertakings."
        ),
        "topic": "sme_reporting",
    },
    {
        "id": "Art.15",
        "title": "Non-EU parent undertakings",
        "keywords": ["non-EU", "third country", "parent company", "150 million", "EU turnover", "subsidiary", "branch"],
        "text": (
            "Undertakings whose parent undertaking is governed by the law of a third country "
            "and which generate a net turnover of more than EUR 150 million in the EU for each "
            "of the last two consecutive financial years shall ensure that consolidated "
            "sustainability information is published. This obligation applies from "
            "financial years beginning on or after 1 January 2028."
        ),
        "topic": "non_eu_parent",
    },
    {
        "id": "Art.16",
        "title": "Information to employee representatives",
        "keywords": ["employee", "worker", "trade union", "information", "consultation", "representative"],
        "text": (
            "Undertakings shall make available the sustainability statement to employee "
            "representatives at an early stage. Employees and employee representatives have the "
            "right to receive the sustainability statement within a reasonable time and to "
            "provide their views on sustainability matters to the governing bodies."
        ),
        "topic": "employee_information",
    },
    {
        "id": "Art.17",
        "title": "Interoperability with international standards",
        "keywords": ["ISSB", "GRI", "TCFD", "interoperability", "international standard", "global baseline", "IFRS"],
        "text": (
            "The Commission shall promote the international acceptance of European Sustainability "
            "Reporting Standards and shall assess the interoperability of ESRS with the IFRS "
            "Sustainability Disclosure Standards (ISSB) and the Global Reporting Initiative (GRI). "
            "Companies reporting under CSRD should be able to satisfy requirements under ISSB "
            "standards with limited additional effort where the standards converge."
        ),
        "topic": "international_interoperability",
    },
]
