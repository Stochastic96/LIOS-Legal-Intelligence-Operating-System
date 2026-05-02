"""Knowledge map — tracks LIOS learning progress across EU and German law topics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_MAP_FILE = Path("data/memory/knowledge_map.json")
_lock = Lock()

_STATUS_ORDER = ["unknown", "seed", "learning", "connected", "functional", "mastered"]

# ── Topic seed map — EU + German law only ─────────────────────────────────────

_SEED_MAP: list[dict] = [
    # EU Sustainability Reporting
    {"id": "csrd", "name": "CSRD", "category": "EU Sustainability Law",
     "status": "functional", "pct": 80, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Corporate Sustainability Reporting Directive 2022/2464 — mandatory sustainability reporting for large EU undertakings"},
    {"id": "esrs", "name": "ESRS Standards", "category": "EU Sustainability Law",
     "status": "functional", "pct": 70, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "European Sustainability Reporting Standards — 12 standards covering environment, social, governance disclosures"},
    {"id": "eu_taxonomy", "name": "EU Taxonomy", "category": "EU Sustainability Law",
     "status": "learning", "pct": 50, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "EU Taxonomy Regulation 2020/852 — classification of environmentally sustainable economic activities"},
    {"id": "sfdr", "name": "SFDR", "category": "EU Sustainability Law",
     "status": "learning", "pct": 40, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Sustainable Finance Disclosure Regulation 2019/2088 — Article 6, 8, 9 fund classification"},
    {"id": "cs3d", "name": "CS3D / CSDDD", "category": "EU Sustainability Law",
     "status": "seed", "pct": 10, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Corporate Sustainability Due Diligence Directive — human rights and environmental due diligence obligations"},
    {"id": "eudr", "name": "EUDR", "category": "EU Sustainability Law",
     "status": "seed", "pct": 5, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "EU Deforestation Regulation 2023/1115 — no-deforestation supply chain obligations"},
    {"id": "green_deal", "name": "European Green Deal", "category": "EU Sustainability Law",
     "status": "seed", "pct": 10, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "EU policy framework targeting climate neutrality by 2050 — Fit for 55, REPowerEU"},
    {"id": "ied", "name": "Industrial Emissions Directive", "category": "EU Sustainability Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "IED 2010/75/EU — integrated pollution prevention and control for industrial installations"},
    {"id": "reach", "name": "REACH Regulation", "category": "EU Sustainability Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "REACH 1907/2006 — Registration, Evaluation, Authorisation of Chemicals"},

    # EU Financial & Corporate Law
    {"id": "mifid2", "name": "MiFID II", "category": "EU Financial Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Markets in Financial Instruments Directive II — investment services, ESG integration requirements"},
    {"id": "srd2", "name": "Shareholder Rights Directive II", "category": "EU Financial Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "SRD II 2017/828 — shareholder engagement, say-on-pay, related party transactions"},
    {"id": "eu_whistleblower", "name": "EU Whistleblower Directive", "category": "EU Financial Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Directive 2019/1937 — protection of persons reporting breaches of EU law"},
    {"id": "gdpr", "name": "GDPR", "category": "EU Financial Law",
     "status": "learning", "pct": 35, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "General Data Protection Regulation 2016/679 — personal data rights and corporate obligations"},
    {"id": "eu_competition", "name": "EU Competition Law", "category": "EU Financial Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "TFEU Articles 101-102 — cartels, abuse of dominant position, merger control"},

    # German National Law
    {"id": "lksg", "name": "LkSG — Supply Chain Act", "category": "German Law",
     "status": "learning", "pct": 30, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Lieferkettensorgfaltspflichtengesetz — human rights and environmental due diligence for German companies"},
    {"id": "behg", "name": "BEHG — Carbon Pricing", "category": "German Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Brennstoffemissionshandelsgesetz — German national carbon pricing for heating and transport fuels"},
    {"id": "ksg", "name": "KSG — Climate Protection Act", "category": "German Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Klimaschutzgesetz — Germany's legally binding annual CO2 reduction targets by sector"},
    {"id": "german_corporate", "name": "GmbHG / AktG", "category": "German Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "GmbH-Gesetz and Aktiengesetz — German corporate law, director duties, Aufsichtsrat, Vorstand"},
    {"id": "hgb", "name": "HGB — Commercial Code", "category": "German Law",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Handelsgesetzbuch — German commercial code, accounting obligations, financial reporting"},
    {"id": "bgb_contracts", "name": "BGB — Contract Law", "category": "German Law",
     "status": "seed", "pct": 15, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Bürgerliches Gesetzbuch — German civil code, contract formation, liability, damages (Schadensersatz)"},

    # Legal Foundations (EU-wide)
    {"id": "eu_legal_terms", "name": "EU Legal Vocabulary", "category": "Legal Foundations",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Core EU legal terms: Richtlinie vs Verordnung, subsidiarity, proportionality, preliminary ruling (CJEU)"},
    {"id": "cjeu_cases", "name": "CJEU Environmental Cases", "category": "Legal Foundations",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Court of Justice of the EU landmark rulings on environmental and corporate sustainability law"},
    {"id": "greenwashing_law", "name": "Greenwashing Law", "category": "Legal Foundations",
     "status": "learning", "pct": 40, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "EU Green Claims Directive, UWG §5 misleading claims, FTC analogues — legal standard for environmental claims"},
    {"id": "double_materiality", "name": "Double Materiality", "category": "Legal Foundations",
     "status": "learning", "pct": 55, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "CSRD/ESRS requirement — impact materiality + financial materiality assessment"},

    # Global Frameworks (kept only where EU-relevant)
    {"id": "gri", "name": "GRI Standards", "category": "Global Frameworks",
     "status": "learning", "pct": 45, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Global Reporting Initiative — voluntary sustainability reporting, compatible with ESRS"},
    {"id": "tcfd", "name": "TCFD", "category": "Global Frameworks",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "Task Force on Climate-related Financial Disclosures — 4 pillars, baseline for ESRS E1"},
    {"id": "issb", "name": "ISSB / IFRS S1 S2", "category": "Global Frameworks",
     "status": "unknown", "pct": 0, "questions_asked": 0, "questions_answered": 0, "last_updated": None,
     "description": "International Sustainability Standards Board — IFRS S1 general, IFRS S2 climate disclosures"},
]

# ── Question bank — 3 types per topic ─────────────────────────────────────────
# Types: "definition" | "application" | "case"

_QUESTION_BANK: dict[str, list[dict]] = {
    "csrd": [
        {"type": "definition", "q": "What is the CSRD and what does it replace?"},
        {"type": "application", "q": "A German AG has 400 employees, €80M turnover, €45M balance sheet. Does CSRD apply from 2025?"},
        {"type": "application", "q": "A listed SME with 150 employees wants to opt out of CSRD until 2028. Is this allowed?"},
        {"type": "definition", "q": "What is Article 19a of CSRD and what must it contain?"},
        {"type": "case", "q": "A company publishes a sustainability statement but omits Scope 3 emissions because data is unavailable. Is this CSRD-compliant?"},
        {"type": "definition", "q": "What are the three phased entry-into-force dates under CSRD?"},
        {"type": "application", "q": "A non-EU parent company has a large EU subsidiary. From when does CSRD apply to the group?"},
    ],
    "esrs": [
        {"type": "definition", "q": "What is the difference between ESRS 1 and ESRS 2?"},
        {"type": "definition", "q": "Name the 5 environmental ESRS standards (E1–E5) and what each covers."},
        {"type": "application", "q": "A company has no material climate risks. Must it still report under ESRS E1?"},
        {"type": "case", "q": "An auditor finds a company reported only financial materiality but skipped impact materiality. Which ESRS is violated?"},
        {"type": "definition", "q": "What does ESRS G1 cover and who does it apply to?"},
        {"type": "application", "q": "Which ESRS standard covers a company's own workforce — pay equity, working conditions, trade unions?"},
    ],
    "eu_taxonomy": [
        {"type": "definition", "q": "What are the 6 environmental objectives of the EU Taxonomy Regulation?"},
        {"type": "definition", "q": "What does DNSH (Do No Significant Harm) mean in the EU Taxonomy?"},
        {"type": "application", "q": "A wind energy company claims Taxonomy alignment. What three criteria must it satisfy?"},
        {"type": "case", "q": "A bank finances a gas power plant and claims it is Taxonomy-aligned as a transition activity. What conditions apply?"},
        {"type": "definition", "q": "What KPIs must non-financial undertakings under CSRD disclose for EU Taxonomy?"},
    ],
    "sfdr": [
        {"type": "definition", "q": "What is the difference between an Article 8 and an Article 9 fund under SFDR?"},
        {"type": "definition", "q": "What are Principal Adverse Impact (PAI) indicators under SFDR?"},
        {"type": "application", "q": "An Article 9 fund holds 5% in bonds with no sustainability objective. Does it remain Article 9?"},
        {"type": "case", "q": "A fund manager markets a product as 'sustainable' without SFDR Article 8 classification. What is the legal risk?"},
        {"type": "definition", "q": "Who does SFDR apply to — all EU companies or specific entities?"},
    ],
    "lksg": [
        {"type": "definition", "q": "What is the LkSG and which companies does it apply to?"},
        {"type": "application", "q": "A German GmbH has 2,800 employees. From which year does LkSG apply?"},
        {"type": "definition", "q": "Does LkSG cover only direct suppliers or the full supply chain?"},
        {"type": "case", "q": "A company's supplier in Bangladesh violates child labour laws. What must the German parent company do under LkSG?"},
        {"type": "application", "q": "What happens if a company fails to conduct the LkSG risk analysis? Name the penalty."},
        {"type": "definition", "q": "What is a 'Beschwerdeverfahren' under LkSG and who must establish one?"},
    ],
    "german_corporate": [
        {"type": "definition", "q": "What is the difference between a GmbH and an AG under German law?"},
        {"type": "definition", "q": "What is the Aufsichtsrat and how does it differ from the Vorstand?"},
        {"type": "application", "q": "A GmbH wants to distribute profits without a shareholder resolution. Is this lawful under GmbHG?"},
        {"type": "definition", "q": "What is Mitbestimmung (codetermination) and when does it apply to German companies?"},
        {"type": "case", "q": "A Vorstand member enters a contract that personally benefits them without board approval. What is the legal consequence under AktG?"},
        {"type": "definition", "q": "What is the minimum share capital for a GmbH vs an AG in Germany?"},
    ],
    "bgb_contracts": [
        {"type": "definition", "q": "What are the three elements required to form a valid contract under BGB §145?"},
        {"type": "definition", "q": "What is Schadensersatz and when does it arise under BGB §280?"},
        {"type": "application", "q": "A company signs a contract under duress (Drohung). What remedy is available under BGB?"},
        {"type": "case", "q": "A supplier delivers defective goods. The buyer wants to cancel the contract. What BGB provisions apply and in what order?"},
        {"type": "definition", "q": "What is the difference between Anfechtung and Rücktritt under BGB?"},
    ],
    "gdpr": [
        {"type": "definition", "q": "What are the 6 lawful bases for processing personal data under GDPR Article 6?"},
        {"type": "application", "q": "A company processes employee health data for payroll. Which GDPR Article applies and what extra condition is needed?"},
        {"type": "definition", "q": "What is the maximum GDPR fine and how is it calculated?"},
        {"type": "case", "q": "An employee asks a company to delete all their data under GDPR Article 17. The company refuses citing legal obligations. Is this lawful?"},
        {"type": "definition", "q": "What is a Data Protection Impact Assessment (DPIA) and when is it mandatory?"},
    ],
    "greenwashing_law": [
        {"type": "definition", "q": "What is greenwashing under EU consumer law and which directive addresses it?"},
        {"type": "application", "q": "A company claims its product is 'carbon neutral' based on offsets alone. Under the EU Green Claims Directive, is this claim valid?"},
        {"type": "case", "q": "An airline advertises 'sustainable flights' without substantiation. Which German law (UWG) provision could apply?"},
        {"type": "definition", "q": "What must a company prove to make a valid environmental claim under the proposed EU Green Claims Directive?"},
        {"type": "application", "q": "A retailer uses a private eco-label not approved under EU law. What is the legal risk post-2026?"},
    ],
    "eu_legal_terms": [
        {"type": "definition", "q": "What is the difference between an EU Richtlinie (Directive) and a Verordnung (Regulation)?"},
        {"type": "definition", "q": "What is the subsidiarity principle in EU law and where is it found in the Treaties?"},
        {"type": "definition", "q": "What is a preliminary ruling (Vorabentscheidungsverfahren) and which court issues it?"},
        {"type": "application", "q": "An EU Regulation is passed but Germany has not transposed it. Does it apply to German companies?"},
        {"type": "definition", "q": "What is the proportionality principle in EU law and how does it limit EU action?"},
        {"type": "definition", "q": "What is direct effect in EU law? Give one example of a provision with direct effect."},
        {"type": "case", "q": "A German court disagrees with how to interpret an EU Directive. What must it do before ruling?"},
    ],
    "double_materiality": [
        {"type": "definition", "q": "What are the two dimensions of double materiality under CSRD/ESRS?"},
        {"type": "application", "q": "A company identifies that its factories pollute local rivers (impact) but this does not affect its financial results. Must it report this under ESRS?"},
        {"type": "case", "q": "A company only conducts financial materiality assessment and omits impact materiality. Which ESRS standard does this violate?"},
        {"type": "definition", "q": "What is IRO (Impact, Risk, Opportunity) analysis and how does it relate to double materiality?"},
    ],
    "tcfd": [
        {"type": "definition", "q": "What are the 4 TCFD pillars — Governance, Strategy, Risk Management, and what is the fourth?"},
        {"type": "application", "q": "A company uses TCFD as its climate disclosure framework. Is this sufficient to comply with ESRS E1?"},
        {"type": "definition", "q": "What is the difference between physical climate risk and transition climate risk under TCFD?"},
        {"type": "case", "q": "An investor asks a company for TCFD-aligned disclosures. The company has no climate strategy. What is the minimum it must disclose?"},
    ],
    "cjeu_cases": [
        {"type": "definition", "q": "What was decided in Case C-237/07 (Janecek) regarding EU environmental law and individual rights?"},
        {"type": "definition", "q": "What is the significance of the 'Urgenda' style cases for EU environmental law obligations?"},
        {"type": "application", "q": "A Member State fails to implement an EU Environmental Directive. What can an individual company do under CJEU precedent?"},
        {"type": "definition", "q": "What is the Francovich principle and when can a company claim damages from a Member State?"},
    ],
    "cs3d": [
        {"type": "definition", "q": "What is CS3D and how does it differ from LkSG?"},
        {"type": "application", "q": "A company with 1,000 EU employees and €450M turnover — does CS3D apply?"},
        {"type": "definition", "q": "Does CS3D require companies to monitor only direct suppliers or the entire value chain?"},
        {"type": "case", "q": "A company's Tier 2 supplier violates ILO conventions. What must the company do under CS3D?"},
    ],
    "hgb": [
        {"type": "definition", "q": "What is the Lagebericht under HGB and who must prepare it?"},
        {"type": "application", "q": "A German GmbH has €6M turnover, 25 employees. Which HGB size class applies?"},
        {"type": "definition", "q": "What is the Grundsatz der Vorsicht (prudence principle) in HGB accounting?"},
        {"type": "case", "q": "A company switches accounting policy from HGB to IFRS. What HGB disclosure obligations apply?"},
    ],
    "ksg": [
        {"type": "definition", "q": "What annual CO2 reduction targets does the KSG set and for which sectors?"},
        {"type": "application", "q": "The German transport sector exceeds its KSG annual emissions budget. What legal consequence follows?"},
        {"type": "definition", "q": "What is the Klimaschutzprogramm and which government body is responsible?"},
    ],
    "behg": [
        {"type": "definition", "q": "What fuels does the BEHG cover and from what year did national CO2 pricing start?"},
        {"type": "application", "q": "A heating oil supplier sells 500,000 tonnes CO2-equivalent. What is its BEHG obligation?"},
        {"type": "definition", "q": "How does BEHG interact with the EU ETS — can emissions be counted twice?"},
    ],
    "gri": [
        {"type": "definition", "q": "What are the GRI Universal Standards and how do they relate to topic-specific standards?"},
        {"type": "application", "q": "A company uses GRI Standards for its sustainability report. Is this sufficient for CSRD compliance?"},
        {"type": "definition", "q": "What is the GRI materiality principle and how does it differ from ESRS double materiality?"},
    ],
    "issb": [
        {"type": "definition", "q": "What is the difference between IFRS S1 and IFRS S2?"},
        {"type": "application", "q": "An EU-listed company already reports under ISSB. Does this satisfy ESRS requirements?"},
        {"type": "definition", "q": "Which jurisdiction first made ISSB-aligned reporting mandatory and from when?"},
    ],
    "eu_whistleblower": [
        {"type": "definition", "q": "Which companies must establish internal whistleblower channels under the EU Whistleblower Directive?"},
        {"type": "application", "q": "An employee reports CSRD fraud internally but faces retaliation. What protection does the Directive provide?"},
        {"type": "definition", "q": "What is the deadline for Member States to implement the EU Whistleblower Directive?"},
    ],
    "reach": [
        {"type": "definition", "q": "What does REACH require companies to do with chemical substances above 1 tonne/year?"},
        {"type": "application", "q": "A company imports a product containing SVHC above 0.1% weight. What REACH obligation applies?"},
        {"type": "definition", "q": "What is the difference between REACH Registration, Authorisation, and Restriction?"},
    ],
    "eu_competition": [
        {"type": "definition", "q": "What does TFEU Article 101 prohibit and what is the exception under Article 101(3)?"},
        {"type": "application", "q": "Two competing companies agree to share sustainability cost data. Could this violate Article 101?"},
        {"type": "definition", "q": "What is the dominance threshold under EU competition law and what does Article 102 prohibit?"},
        {"type": "case", "q": "A large tech company refuses to grant access to its platform to a sustainability data provider. Which TFEU article applies?"},
    ],
    "mifid2": [
        {"type": "definition", "q": "What sustainability-related amendments did MiFID II receive and from when?"},
        {"type": "application", "q": "An investment advisor does not ask clients about ESG preferences. Does this comply with MiFID II post-2022?"},
        {"type": "definition", "q": "What is a sustainability preference under MiFID II and what three options can a client choose?"},
    ],
    "ied": [
        {"type": "definition", "q": "What is a Best Available Technique (BAT) under the IED and who sets it?"},
        {"type": "application", "q": "A factory exceeds its IED emission limit values. What is the competent authority's response?"},
        {"type": "definition", "q": "Which industrial installations require an IED permit in Germany?"},
    ],
    "srd2": [
        {"type": "definition", "q": "What shareholder engagement obligations does SRD II impose on institutional investors?"},
        {"type": "application", "q": "A company pays its CEO 300x the median employee wage. What SRD II disclosure is required?"},
        {"type": "definition", "q": "What is a related party transaction under SRD II and when does shareholder approval apply?"},
    ],
}


def _load() -> list[dict]:
    if _MAP_FILE.exists():
        try:
            data = json.loads(_MAP_FILE.read_text())
            # Migrate: add any new seed topics not yet in saved map
            saved_ids = {t["id"] for t in data}
            for seed in _SEED_MAP:
                if seed["id"] not in saved_ids:
                    data.append(dict(seed))
            return data
        except Exception:
            pass
    return [dict(t) for t in _SEED_MAP]


def _save(topics: list[dict]) -> None:
    _MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MAP_FILE.write_text(json.dumps(topics, indent=2, ensure_ascii=False))


def get_map() -> list[dict]:
    with _lock:
        return _load()


def get_overall_pct() -> int:
    topics = get_map()
    if not topics:
        return 0
    return round(sum(t["pct"] for t in topics) / len(topics))


def get_next_learn_topic() -> dict | None:
    topics = get_map()
    learnable = [t for t in topics if t["status"] not in ("functional", "mastered")]
    if not learnable:
        return None
    learnable.sort(key=lambda t: (_STATUS_ORDER.index(t.get("status", "unknown")), t["pct"]))
    return learnable[0]


def get_next_question(topic_id: str) -> dict | None:
    """Return next unanswered question dict {type, q} for a topic."""
    questions = _QUESTION_BANK.get(topic_id, [])
    if not questions:
        return None
    topics = get_map()
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        return None
    asked = topic.get("questions_asked", 0)
    idx = asked % len(questions)
    return questions[idx]


def get_all_questions(topic_id: str) -> list[dict]:
    """Return all questions for a topic — used by bootstrap learner."""
    return _QUESTION_BANK.get(topic_id, [])


def record_answer(topic_id: str, answer_text: str, reference: str = "") -> dict:
    with _lock:
        topics = _load()
        for topic in topics:
            if topic["id"] == topic_id:
                topic["questions_asked"] = topic.get("questions_asked", 0) + 1
                topic["questions_answered"] = topic.get("questions_answered", 0) + 1
                topic["last_updated"] = datetime.now(timezone.utc).isoformat()
                topic["pct"] = min(100, topic["pct"] + 12)
                topic["status"] = _compute_status(topic["pct"])
                _save(topics)
                return topic
        return {}


def _compute_status(pct: int) -> str:
    if pct == 0:
        return "unknown"
    if pct < 20:
        return "seed"
    if pct < 50:
        return "learning"
    if pct < 70:
        return "connected"
    if pct < 90:
        return "functional"
    return "mastered"
