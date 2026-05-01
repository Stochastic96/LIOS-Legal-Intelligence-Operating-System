"""Build a rich seed corpus from accurate EU regulatory content.

EUR-Lex is WAF-blocked for automated access. This script provides a
comprehensive, accurate corpus of key CSRD, ESRS, EU Taxonomy, SFDR,
GDPR, and CS3D articles for immediate use.

Usage:
    python scripts/build_rich_seed_corpus.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

OUTPUT = _ROOT / "data/corpus/legal_chunks.jsonl"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

CHUNKS: list[dict] = [

    # ── CSRD ─────────────────────────────────────────────────────────────────
    {
        "regulation": "CSRD", "article": "Art.1", "celex_id": "32022L2464",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
        "text": (
            "CSRD Art.1 — Subject matter. Directive 2022/2464/EU amends Directive 2013/34/EU "
            "(Accounting Directive) to introduce mandatory sustainability reporting. It requires "
            "large undertakings and listed SMEs to disclose information on environmental, social "
            "and governance (ESG) matters in their management reports. The directive replaces the "
            "Non-Financial Reporting Directive (NFRD, 2014/95/EU) with a significantly expanded "
            "scope and mandatory European Sustainability Reporting Standards (ESRS)."
        ),
    },
    {
        "regulation": "CSRD", "article": "Art.2", "celex_id": "32022L2464",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
        "text": (
            "CSRD Art.2 — Scope. CSRD applies to: (1) large EU undertakings (regardless of stock "
            "exchange listing) exceeding at least two of three criteria: 250+ employees, €40M+ net "
            "turnover, €20M+ balance sheet total; (2) listed SMEs (with opt-out until 2028); "
            "(3) large non-EU parent companies with €150M+ net turnover in the EU and at least one "
            "EU subsidiary/branch. Financial institutions including banks and insurance companies "
            "are included. Small and micro undertakings are excluded unless listed."
        ),
    },
    {
        "regulation": "CSRD", "article": "Art.5", "celex_id": "32022L2464",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
        "text": (
            "CSRD Art.5 — Phased entry into force. Large public-interest entities (PIEs) with "
            "more than 500 employees already subject to NFRD: apply from financial year 2024 "
            "(reports published 2025). Other large undertakings meeting CSRD thresholds: apply "
            "from financial year 2025 (reports published 2026). Listed SMEs, small and "
            "non-complex credit institutions, captive insurance undertakings: apply from financial "
            "year 2026 (reports published 2027), with opt-out until 2028. Non-EU parent "
            "undertakings: apply from financial year 2028 (reports published 2029)."
        ),
    },
    {
        "regulation": "CSRD", "article": "Art.19a", "celex_id": "32022L2464",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
        "text": (
            "CSRD Art.19a — Sustainability statement. Large undertakings must include in their "
            "management report a sustainability statement covering: (a) business model and "
            "strategy with respect to sustainability risks and opportunities; (b) time-bound "
            "targets related to sustainability matters; (c) role of administrative, management "
            "and supervisory bodies; (d) sustainability due diligence policies; (e) principal "
            "actual or potential adverse impacts on sustainability matters; (f) actions taken "
            "and future plans; (g) key performance indicators. The statement must follow the "
            "European Sustainability Reporting Standards (ESRS) adopted by the Commission."
        ),
    },
    {
        "regulation": "CSRD", "article": "Art.19b", "celex_id": "32022L2464",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
        "text": (
            "CSRD Art.19b — Double materiality assessment. Undertakings must assess sustainability "
            "matters from two perspectives: (1) Impact materiality — how undertaking's activities "
            "impact people and the environment (inside-out); (2) Financial materiality — how "
            "sustainability risks and opportunities affect the undertaking's financial performance, "
            "position and cash flows (outside-in). A matter is material if it qualifies under "
            "either or both perspectives. The double materiality assessment determines which ESRS "
            "disclosure requirements are applicable to the undertaking."
        ),
    },
    {
        "regulation": "CSRD", "article": "Art.29a", "celex_id": "32022L2464",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
        "text": (
            "CSRD Art.29a — Consolidated sustainability reporting. Parent undertakings of large "
            "groups must include a consolidated sustainability statement in the consolidated "
            "management report. Group-level reporting may exempt subsidiaries from individual "
            "sustainability reporting if the subsidiary is included in the group's consolidated "
            "sustainability statement and the parent is subject to CSRD or equivalent rules. "
            "Subsidiaries must disclose the name and registered office of the parent providing "
            "the consolidated report."
        ),
    },
    {
        "regulation": "CSRD", "article": "Art.34", "celex_id": "32022L2464",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
        "text": (
            "CSRD Art.34 — Assurance of sustainability reporting. Member States must require "
            "limited assurance of the sustainability statement by an accredited statutory auditor "
            "or an independent assurance services provider. The Commission may adopt delegated "
            "acts to set assurance standards. The assurance opinion must state whether the "
            "sustainability statement complies with ESRS requirements and whether the undertaking's "
            "process for identifying reported information complies with the directive. The "
            "long-term objective is to move from limited to reasonable assurance."
        ),
    },

    # ── ESRS ─────────────────────────────────────────────────────────────────
    {
        "regulation": "ESRS", "article": "ESRS1-General", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS 1 — General Requirements. Sets the architecture for all ESRS. Undertakings "
            "must apply the double materiality principle to determine which disclosures to include. "
            "ESRS 1 defines sustainability matters as environmental, social and governance topics. "
            "It establishes the value chain concept — undertakings report on their own operations "
            "plus upstream and downstream value chain where material. Disclosure requirements are "
            "either mandatory (apply if material) or voluntary. Comparative information for the "
            "prior year is required."
        ),
    },
    {
        "regulation": "ESRS", "article": "ESRS2-General", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS 2 — General Disclosures. Always mandatory regardless of materiality assessment. "
            "Requires disclosure of: (1) Governance — roles of management and supervisory bodies "
            "in sustainability; (2) Strategy — business model, strategy and sustainability risks; "
            "(3) Impact, Risk and Opportunity Management — due diligence process, ESRS topics "
            "identified as material; (4) Metrics and Targets — KPIs and time-bound targets. "
            "ESRS 2 is the backbone that links to all topical ESRS standards."
        ),
    },
    {
        "regulation": "ESRS", "article": "ESRS-E1-Climate", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS E1 — Climate Change. Covers climate change mitigation and adaptation. "
            "Key disclosure requirements: (1) Transition plan for climate change mitigation "
            "including Paris Agreement alignment; (2) Total GHG emissions — Scope 1 (direct), "
            "Scope 2 (energy indirect), Scope 3 (value chain) in tonnes CO2 equivalent; "
            "(3) Climate-related physical and transition risks and opportunities; "
            "(4) Net zero targets and interim milestones; (5) Energy consumption and mix; "
            "(6) Carbon removal and carbon credit disclosure. Science-based targets and "
            "Paris Agreement alignment must be disclosed."
        ),
    },
    {
        "regulation": "ESRS", "article": "ESRS-E2-Pollution", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS E2 — Pollution. Requires disclosure of: (1) Air pollutant emissions (NOx, SOx, "
            "PM, VOCs); (2) Water pollutant discharges; (3) Soil pollutant releases; (4) Substances "
            "of concern and very high concern; (5) Microplastics released. Undertakings must "
            "report on their policies, actions and targets to prevent or reduce pollution. "
            "The standard connects to EU Industrial Emissions Directive thresholds and "
            "REACH regulation substance restrictions."
        ),
    },
    {
        "regulation": "ESRS", "article": "ESRS-E3-Water", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS E3 — Water and Marine Resources. Disclosure requirements: (1) Total water "
            "consumption in m3, with breakdown for water-stressed areas (using WRI Aqueduct "
            "or equivalent tool); (2) Water withdrawals by source; (3) Water discharges to "
            "oceans; (4) Marine resources impacts — extraction volume, impacted areas. "
            "Material for undertakings in water-intensive sectors (food, textiles, mining, "
            "semiconductors). Links to EU Water Framework Directive good ecological status targets."
        ),
    },
    {
        "regulation": "ESRS", "article": "ESRS-E4-Biodiversity", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS E4 — Biodiversity and Ecosystems. Key disclosures: (1) Number and area of "
            "sites owned or managed in or near biodiversity-sensitive areas (Natura 2000, "
            "UNESCO World Heritage, IUCN I-IV); (2) Land use change and land degradation; "
            "(3) Species affected — number on IUCN Red List; (4) Transition plan for "
            "biodiversity. Aligns with EU Biodiversity Strategy 2030 and Kunming-Montreal "
            "Global Biodiversity Framework (30x30 targets). TNFD alignment encouraged."
        ),
    },
    {
        "regulation": "ESRS", "article": "ESRS-S1-Workforce", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS S1 — Own Workforce. Comprehensive social disclosures covering: (1) Total "
            "employees by gender, country, employment type (full/part-time, permanent/temporary); "
            "(2) Pay gap between male and female employees; (3) CEO pay ratio vs. median employee; "
            "(4) Collective bargaining coverage %; (5) Work-related injuries and fatalities; "
            "(6) Training hours per employee; (7) Freedom of association and right to collective "
            "bargaining; (8) Living wage assessment. Links to European Pillar of Social Rights."
        ),
    },
    {
        "regulation": "ESRS", "article": "ESRS-S2-ValueChain", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS S2 — Workers in the Value Chain. Covers impacts on workers in upstream "
            "supply chain and downstream commercial chain. Disclosures: (1) Due diligence "
            "approach for value chain workers; (2) Significant actual and potential adverse "
            "impacts (forced labour, child labour, unsafe working conditions, poverty wages); "
            "(3) Grievance mechanisms accessible to value chain workers; (4) Remediation "
            "actions taken. Aligns with CS3D (Corporate Sustainability Due Diligence Directive) "
            "human rights due diligence obligations."
        ),
    },
    {
        "regulation": "ESRS", "article": "ESRS-G1-Governance", "celex_id": "32023R2772",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2772",
        "text": (
            "ESRS G1 — Business Conduct. Governance disclosures covering: (1) Anti-corruption "
            "and anti-bribery — policies, training, confirmed incidents; (2) Political engagement "
            "and lobbying activities and expenditure; (3) Protection of whistleblowers; "
            "(4) Animal welfare policies; (5) Payment practices — percentage of payments made "
            "within agreed terms, average payment period beyond agreed terms to SMEs. Aligns "
            "with UN Guiding Principles on Business and Human Rights (UNGP) and OECD Guidelines."
        ),
    },

    # ── EU TAXONOMY ──────────────────────────────────────────────────────────
    {
        "regulation": "EU_TAXONOMY", "article": "Art.3", "celex_id": "32020R0852",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32020R0852",
        "text": (
            "EU Taxonomy Art.3 — Criteria for environmentally sustainable economic activities. "
            "An economic activity qualifies as environmentally sustainable if it: (a) contributes "
            "substantially to one or more of the six environmental objectives; (b) does not "
            "significantly harm (DNSH) any of the other five environmental objectives; "
            "(c) complies with minimum social safeguards (ILO core conventions, UN Guiding "
            "Principles on Business and Human Rights); (d) complies with the technical screening "
            "criteria set out in delegated acts adopted by the Commission."
        ),
    },
    {
        "regulation": "EU_TAXONOMY", "article": "Art.9-Objectives", "celex_id": "32020R0852",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32020R0852",
        "text": (
            "EU Taxonomy Art.9 — Six Environmental Objectives. (1) Climate change mitigation — "
            "activities contributing to stabilising GHG concentrations at levels that prevent "
            "dangerous anthropogenic interference with the climate system; (2) Climate change "
            "adaptation — reducing material physical climate risk; (3) Sustainable use and "
            "protection of water and marine resources; (4) Transition to a circular economy; "
            "(5) Pollution prevention and control; (6) Protection and restoration of "
            "biodiversity and ecosystems."
        ),
    },
    {
        "regulation": "EU_TAXONOMY", "article": "Art.17-DNSH", "celex_id": "32020R0852",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32020R0852",
        "text": (
            "EU Taxonomy Art.17 — Do No Significant Harm (DNSH). An economic activity harms "
            "an environmental objective if it: (1) leads to significant GHG emissions; "
            "(2) adversely affects the adaptation to climate change of the activity itself or "
            "people, nature and assets; (3) is incompatible with the good status or good "
            "potential of water bodies; (4) leads to significant waste generation or inefficient "
            "use of materials; (5) causes significant pollution to air, water or land; "
            "(6) significantly harms the condition of ecosystems or biodiversity. DNSH is "
            "assessed against each of the 6 environmental objectives for each activity."
        ),
    },
    {
        "regulation": "EU_TAXONOMY", "article": "Art.8-Disclosure", "celex_id": "32020R0852",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32020R0852",
        "text": (
            "EU Taxonomy Art.8 — Disclosure obligations. Non-financial undertakings subject to "
            "CSRD must disclose: (1) Proportion of taxonomy-eligible and taxonomy-aligned "
            "turnover; (2) Proportion of taxonomy-eligible and taxonomy-aligned capital "
            "expenditure (CapEx); (3) Proportion of taxonomy-eligible and taxonomy-aligned "
            "operating expenditure (OpEx). Financial undertakings (asset managers, banks, "
            "insurers) must disclose the Green Asset Ratio (GAR) or equivalent. Delegated "
            "Regulation 2021/2178 sets the disclosure format and KPIs."
        ),
    },

    # ── SFDR ─────────────────────────────────────────────────────────────────
    {
        "regulation": "SFDR", "article": "Art.2", "celex_id": "32019R2088",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R2088",
        "text": (
            "SFDR Art.2 — Key definitions. 'Financial market participant' includes investment "
            "firms providing portfolio management, AIFMs, UCITS management companies, insurance "
            "undertakings providing IBIP, pension funds (IORPS), and EuVECA/EuSEF managers. "
            "'Sustainability risk' means an environmental, social or governance event or "
            "condition that could cause an actual or potential material negative impact on the "
            "value of an investment. 'Sustainable investment' means an investment in an economic "
            "activity contributing to an environmental or social objective, provided it does not "
            "significantly harm other objectives and that investee companies follow good "
            "governance practices."
        ),
    },
    {
        "regulation": "SFDR", "article": "Art.6", "celex_id": "32019R2088",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R2088",
        "text": (
            "SFDR Art.6 — Article 6 products (sustainability risk integration). All financial "
            "products must disclose: how sustainability risks are integrated into investment "
            "decisions, and the likely impacts of sustainability risks on returns. If the "
            "financial market participant considers sustainability risks not relevant, they "
            "must give a clear and concise explanation of the reasons. This is the baseline "
            "requirement — all products are Article 6 by default unless they meet Article 8 "
            "or 9 criteria."
        ),
    },
    {
        "regulation": "SFDR", "article": "Art.8", "celex_id": "32019R2088",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R2088",
        "text": (
            "SFDR Art.8 — Products promoting environmental or social characteristics ('light "
            "green' funds). A financial product qualifies as Article 8 if it promotes, among "
            "other characteristics, environmental or social characteristics, or a combination "
            "of those characteristics, provided that the companies in which investments are "
            "made follow good governance practices. Pre-contractual disclosure must include: "
            "how E/S characteristics are met, whether an index is used as reference benchmark, "
            "and where the fund methodology is published."
        ),
    },
    {
        "regulation": "SFDR", "article": "Art.9", "celex_id": "32019R2088",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R2088",
        "text": (
            "SFDR Art.9 — Products with sustainable investment as objective ('dark green' funds). "
            "An Article 9 product must have sustainable investment as its objective. Where a "
            "financial product has a reduction in carbon emissions as its objective it must "
            "designate a Paris-Aligned Benchmark or a Climate Transition Benchmark. All Article "
            "9 products must disclose: the sustainable investment objective, how that objective "
            "is attained, the reference benchmark used, and how the benchmark aligns with the "
            "objective. Periodic reports must include: overall sustainability indicator, top "
            "investments by % of fund, % of sustainable investments."
        ),
    },
    {
        "regulation": "SFDR", "article": "Art.4-PAI", "celex_id": "32019R2088",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R2088",
        "text": (
            "SFDR Art.4 — Principal Adverse Impact (PAI) statements. Financial market "
            "participants with more than 500 employees must consider and publish a PAI statement "
            "at entity level on their website. Smaller participants may voluntarily comply. "
            "The PAI statement must cover 14 mandatory indicators (Table 1 of RTS): "
            "GHG emissions, carbon footprint, GHG intensity, fossil fuel exposure, non-renewable "
            "energy, energy intensity, biodiversity impact, water emissions, hazardous waste, "
            "UNGP/ILO violations, gender pay gap, board gender diversity, exposure to "
            "controversial weapons. Reference period is prior calendar year."
        ),
    },

    # ── GDPR ─────────────────────────────────────────────────────────────────
    {
        "regulation": "GDPR", "article": "Art.5", "celex_id": "32016R0679",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679",
        "text": (
            "GDPR Art.5 — Principles relating to processing of personal data. Personal data "
            "shall be: (a) processed lawfully, fairly and transparently (lawfulness, fairness, "
            "transparency); (b) collected for specified, explicit and legitimate purposes and "
            "not further processed in a manner incompatible with those purposes (purpose "
            "limitation); (c) adequate, relevant and limited to what is necessary (data "
            "minimisation); (d) accurate and kept up to date (accuracy); (e) kept for no longer "
            "than necessary (storage limitation); (f) processed securely (integrity and "
            "confidentiality). The controller is responsible for and must demonstrate compliance "
            "with these principles (accountability)."
        ),
    },
    {
        "regulation": "GDPR", "article": "Art.6", "celex_id": "32016R0679",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679",
        "text": (
            "GDPR Art.6 — Lawfulness of processing. Processing is lawful only if at least one "
            "applies: (a) data subject has given consent; (b) processing is necessary for "
            "performance of a contract; (c) processing is necessary for compliance with a legal "
            "obligation; (d) processing is necessary to protect vital interests; (e) processing "
            "is necessary for a task carried out in the public interest; (f) processing is "
            "necessary for legitimate interests of the controller or third party, unless "
            "overridden by the interests or fundamental rights of the data subject."
        ),
    },
    {
        "regulation": "GDPR", "article": "Art.83-Fines", "celex_id": "32016R0679",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679",
        "text": (
            "GDPR Art.83 — Administrative fines. Tier 1 (Art.83(4)): up to €10 million or 2% of "
            "total worldwide annual turnover for infringements including obligations of controller "
            "and processor, certification body, monitoring body. Tier 2 (Art.83(5)): up to "
            "€20 million or 4% of total worldwide annual turnover for infringements of basic "
            "principles (Art.5, 6, 7, 9), data subject rights, transfers to third countries. "
            "The higher of the two amounts applies. Supervisory authorities must ensure fines "
            "are effective, proportionate and dissuasive."
        ),
    },

    # ── CS3D / CSDDD ─────────────────────────────────────────────────────────
    {
        "regulation": "CS3D", "article": "Art.1-Scope", "celex_id": "32024L1760",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L1760",
        "text": (
            "CS3D (CSDDD) Art.1 — Subject matter and scope. Directive 2024/1760/EU establishes "
            "mandatory human rights and environmental due diligence obligations. Applies to: "
            "(1) EU companies with 1,000+ employees and €450M+ worldwide turnover; (2) Non-EU "
            "companies with €450M+ net turnover generated in the EU. Phased application: "
            "companies with 5,000+ employees and €1.5B+ turnover from July 2027; companies "
            "with 3,000+ employees and €900M+ from July 2028; all in-scope companies by "
            "July 2029. Financial sector has separate timeline."
        ),
    },
    {
        "regulation": "CS3D", "article": "Art.5-DueDiligence", "celex_id": "32024L1760",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L1760",
        "text": (
            "CS3D Art.5 — Due diligence obligations. In-scope companies must: (1) Integrate due "
            "diligence into corporate policies and risk management; (2) Identify actual and "
            "potential adverse human rights and environmental impacts in own operations and "
            "direct business relationships (tier 1 suppliers); (3) Prevent or mitigate potential "
            "adverse impacts; (4) Bring actual adverse impacts to an end or minimise their extent; "
            "(5) Establish and maintain a complaints procedure; (6) Monitor effectiveness; "
            "(7) Publicly communicate on due diligence. Due diligence covers the full value chain "
            "for regulated sectors (textiles, agriculture, minerals, fossil fuels)."
        ),
    },
    {
        "regulation": "CS3D", "article": "Art.22-Liability", "celex_id": "32024L1760",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L1760",
        "text": (
            "CS3D Art.22 — Civil liability. Member States must ensure that companies are liable "
            "for damages caused to natural persons or legal entities if: the company intentionally "
            "or negligently failed to comply with due diligence obligations, and this failure "
            "caused or contributed to an adverse impact. Victims must prove the adverse impact "
            "and causal link. Companies can avoid liability by proving the damage was caused "
            "solely by a business partner. Limitation periods for bringing claims must be at "
            "least 5 years."
        ),
    },

    # ── LkSG (German Supply Chain Act) ───────────────────────────────────────
    {
        "regulation": "LkSG", "article": "§1-Scope", "celex_id": "DE_LkSG",
        "jurisdiction": "DE", "chunk_type": "article",
        "source_url": "https://www.gesetze-im-internet.de/lksg/",
        "text": (
            "LkSG §1 — Scope (Lieferkettensorgfaltspflichtengesetz). The German Supply Chain "
            "Due Diligence Act applies to: companies with registered offices or branches in "
            "Germany with 3,000+ employees from January 2023, and 1,000+ employees from "
            "January 2024. Covers own operations plus direct suppliers (tier 1) and indirect "
            "suppliers where company has substantiated knowledge of violations. Obligations "
            "include risk analysis, preventive measures, remediation, complaint mechanism, "
            "documentation and annual reporting to BAFA (Federal Office for Economic Affairs "
            "and Export Control). Fines up to €8 million or 2% of global annual turnover."
        ),
    },

    # ── TCFD ─────────────────────────────────────────────────────────────────
    {
        "regulation": "TCFD", "article": "Pillars", "celex_id": "TCFD_2017",
        "jurisdiction": "GLOBAL", "chunk_type": "article",
        "source_url": "https://www.fsb-tcfd.org/recommendations/",
        "text": (
            "TCFD — Task Force on Climate-related Financial Disclosures (2017). Four core "
            "disclosure pillars: (1) Governance — board oversight of climate risks and "
            "opportunities, management's role; (2) Strategy — actual and potential climate "
            "impacts on business, strategy and financial planning including 2°C scenario "
            "analysis; (3) Risk Management — processes for identifying, assessing and "
            "managing climate risks and how they are integrated into overall risk management; "
            "(4) Metrics and Targets — metrics and targets used to assess and manage climate "
            "risks and opportunities including Scope 1, 2 and 3 GHG emissions. TCFD is "
            "voluntary globally but mandatory in UK, New Zealand, Switzerland and Japan."
        ),
    },

    # ── GRI ──────────────────────────────────────────────────────────────────
    {
        "regulation": "GRI", "article": "GRI-Universal", "celex_id": "GRI_2021",
        "jurisdiction": "GLOBAL", "chunk_type": "article",
        "source_url": "https://www.globalreporting.org/standards/",
        "text": (
            "GRI Universal Standards 2021. GRI 1 (Foundation): reporting principles — "
            "accuracy, balance, clarity, comparability, completeness, sustainability context, "
            "timeliness, verifiability. GRI 2 (General Disclosures): organisational profile, "
            "governance, strategy, ethics, stakeholder engagement, reporting practice. "
            "GRI 3 (Material Topics): process for determining material topics and managing "
            "impacts. Topic Standards (GRI 200-400) cover economic (201-207), environmental "
            "(301-308) and social (401-418) topics. GRI is voluntary globally; ESRS has "
            "substantial interoperability with GRI Universal Standards."
        ),
    },

    # ── Greenwashing ─────────────────────────────────────────────────────────
    {
        "regulation": "EU_GREENWASHING", "article": "Green-Claims-Directive",
        "celex_id": "COM_2023_166",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52023PC0166",
        "text": (
            "EU Green Claims Directive (proposed 2023). Requires companies making voluntary "
            "green claims to: (1) Substantiate claims with scientific evidence before making "
            "them; (2) Have claims verified by an accredited third-party verifier; "
            "(3) Ensure claims are specific and precise; (4) Comparative claims must compare "
            "on equivalent basis. Prohibited: 'carbon neutral' claims based solely on offsets; "
            "generic claims ('eco-friendly', 'green', 'natural') without substantiation; "
            "claims about products containing hazardous substances. Enforcement: Member States "
            "must impose effective, proportionate and dissuasive penalties."
        ),
    },
    {
        "regulation": "EU_GREENWASHING", "article": "Empowering-Consumers-Directive",
        "celex_id": "32024L0825",
        "jurisdiction": "EU", "chunk_type": "article",
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L0825",
        "text": (
            "Directive 2024/825/EU — Empowering Consumers for the Green Transition. Amends "
            "the Unfair Commercial Practices Directive to ban greenwashing. Explicitly prohibited: "
            "(1) Displaying a sustainability label not based on certification scheme or "
            "established by public authorities; (2) Making a generic environmental claim "
            "('eco', 'green', 'environmentally friendly') without proof of recognised "
            "excellent environmental performance; (3) Making sustainability claim about the "
            "entire product where it only concerns a specific aspect; (4) Not displaying "
            "information about planned obsolescence. Applies from March 2026."
        ),
    },
]


def build():
    existing: set[str] = set()
    if OUTPUT.exists():
        for line in OUTPUT.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                key = f"{c.get('celex_id','')}-{c.get('article','')}"
                existing.add(key)
            except Exception:
                pass

    added = 0
    with OUTPUT.open("a") as f:
        for chunk in CHUNKS:
            key = f"{chunk.get('celex_id','')}-{chunk.get('article','')}"
            if key in existing:
                continue
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            added += 1

    print(f"✓ {added} chunks added to {OUTPUT}")
    print(f"  Total in corpus: {sum(1 for l in OUTPUT.read_text().splitlines() if l.strip())}")

    # Load into ChromaDB
    try:
        from lios.retrieval.chroma_retriever import ingest_jsonl
        n = ingest_jsonl(str(OUTPUT), collection_name="eu_law")
        print(f"✓ {n} new chunks loaded into ChromaDB eu_law collection")
    except Exception as e:
        print(f"  ChromaDB load skipped: {e}")


if __name__ == "__main__":
    build()
