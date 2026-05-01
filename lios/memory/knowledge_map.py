"""Knowledge map — tracks LIOS's learning progress across EU law topics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

_MAP_FILE = Path("data/memory/knowledge_map.json")
_lock = Lock()

# Seed map — all topics LIOS needs to learn, grouped by category
_SEED_MAP: list[dict] = [
    # EU Regulatory Framework
    {"id": "csrd", "name": "CSRD", "category": "EU Framework", "status": "functional", "pct": 80,
     "description": "Corporate Sustainability Reporting Directive (2022/2464)",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "esrs", "name": "ESRS Standards", "category": "EU Framework", "status": "functional", "pct": 70,
     "description": "European Sustainability Reporting Standards (12 cross-cutting + topical standards)",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "eu_taxonomy", "name": "EU Taxonomy", "category": "EU Framework", "status": "learning", "pct": 50,
     "description": "EU Taxonomy Regulation — 6 environmental objectives + do no significant harm",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "sfdr", "name": "SFDR", "category": "EU Framework", "status": "learning", "pct": 40,
     "description": "Sustainable Finance Disclosure Regulation — Article 6, 8, 9 fund classification",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "cs3d", "name": "CS3D", "category": "EU Framework", "status": "seed", "pct": 10,
     "description": "Corporate Sustainability Due Diligence Directive",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "eudr", "name": "EUDR", "category": "EU Framework", "status": "seed", "pct": 5,
     "description": "EU Deforestation Regulation",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "green_deal", "name": "European Green Deal", "category": "EU Framework", "status": "seed", "pct": 10,
     "description": "EU policy framework targeting climate neutrality by 2050",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    # Global Frameworks
    {"id": "gri", "name": "GRI Standards", "category": "Global Frameworks", "status": "learning", "pct": 45,
     "description": "Global Reporting Initiative — voluntary sustainability reporting standards",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "tcfd", "name": "TCFD", "category": "Global Frameworks", "status": "unknown", "pct": 0,
     "description": "Task Force on Climate-related Financial Disclosures",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "issb", "name": "ISSB / IFRS S1 S2", "category": "Global Frameworks", "status": "unknown", "pct": 0,
     "description": "International Sustainability Standards Board — IFRS S1 general, IFRS S2 climate",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "tnfd", "name": "TNFD", "category": "Global Frameworks", "status": "unknown", "pct": 0,
     "description": "Taskforce on Nature-related Financial Disclosures",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "sbti", "name": "SBTi", "category": "Global Frameworks", "status": "unknown", "pct": 0,
     "description": "Science Based Targets initiative — corporate emissions reduction targets",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    # US Law
    {"id": "sec_esg", "name": "SEC ESG Disclosure", "category": "US Law", "status": "unknown", "pct": 0,
     "description": "SEC climate-related disclosure rules for public companies",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "ftc_green", "name": "FTC Green Guides", "category": "US Law", "status": "unknown", "pct": 0,
     "description": "FTC guidelines on environmental marketing claims (updated 2023)",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "california_climate", "name": "California Climate Laws", "category": "US Law", "status": "unknown", "pct": 0,
     "description": "SB 253, SB 261 — mandatory climate disclosure for large companies in California",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    # Core Concepts
    {"id": "esg_basics", "name": "ESG Fundamentals", "category": "Core Concepts", "status": "functional", "pct": 85,
     "description": "Environmental, Social, Governance — definitions, metrics, materiality",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "greenwashing", "name": "Greenwashing Law", "category": "Core Concepts", "status": "learning", "pct": 40,
     "description": "Legal definition, enforcement, FTC/EU consumer law angles",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "carbon_markets", "name": "Carbon Credits & ETS", "category": "Core Concepts", "status": "learning", "pct": 35,
     "description": "EU ETS, carbon credits, offsets, carbon neutrality vs net-zero",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "double_materiality", "name": "Double Materiality", "category": "Core Concepts", "status": "learning", "pct": 55,
     "description": "Impact materiality + financial materiality — CSRD/ESRS requirement",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
    {"id": "supply_chain_due_diligence", "name": "Supply Chain Due Diligence", "category": "Core Concepts", "status": "seed", "pct": 15,
     "description": "CS3D, CSDDD — human rights and environmental due diligence obligations",
     "questions_asked": 0, "questions_answered": 0, "last_updated": None},
]

# Status ordering for graduation logic
_STATUS_ORDER = ["unknown", "seed", "learning", "connected", "functional", "mastered"]

# Question bank — LIOS asks these to learn from the user
_QUESTION_BANK: dict[str, list[str]] = {
    "tcfd": [
        "TCFD stands for Task Force on Climate-related Financial Disclosures — but what are the 4 core pillars it recommends companies report on?",
        "Is TCFD voluntary globally, or have any jurisdictions made it mandatory? Give me one example.",
        "How does TCFD relate to ISSB IFRS S2 — are they separate frameworks or connected?",
    ],
    "issb": [
        "What is the difference between IFRS S1 and IFRS S2 under the ISSB framework?",
        "Are ISSB standards mandatory or voluntary at the global level?",
        "Which jurisdiction first made ISSB-aligned standards mandatory, and from when?",
    ],
    "sfdr": [
        "What is the difference between an Article 8 fund and an Article 9 fund under SFDR?",
        "Who does SFDR apply to — all EU companies or a specific type of entity?",
        "What is a Principal Adverse Impact (PAI) indicator under SFDR?",
    ],
    "eu_taxonomy": [
        "What are the 6 environmental objectives in the EU Taxonomy Regulation?",
        "What does 'Do No Significant Harm' (DNSH) mean in the EU Taxonomy context?",
        "How does the EU Taxonomy connect to CSRD reporting — are they linked?",
    ],
    "cs3d": [
        "What is the core obligation CS3D places on large EU companies?",
        "What is the employee/revenue threshold for CS3D to apply?",
        "Does CS3D cover only direct suppliers or the full supply chain?",
    ],
    "tcfd": [
        "What are the 4 TCFD pillars — Governance, Strategy, Risk Management, and what is the fourth?",
        "Is TCFD voluntary globally, or have any jurisdictions made it mandatory?",
        "How is TCFD related to ISSB S2?",
    ],
    "greenwashing": [
        "What is the legal definition of greenwashing under EU consumer law?",
        "Which EU directive specifically targets greenwashing claims — and when does it apply?",
        "What is the difference between greenwashing and a genuinely misleading environmental claim?",
    ],
    "carbon_markets": [
        "What is the EU ETS and how does it work in one sentence?",
        "What is the difference between carbon neutral and net-zero?",
        "Are carbon offsets treated the same as carbon reductions under EU law?",
    ],
    "ftc_green": [
        "When were the FTC Green Guides last updated?",
        "What types of environmental claims do the FTC Green Guides regulate?",
        "What happens to a company that violates FTC Green Guides?",
    ],
    "sec_esg": [
        "What did the SEC propose in its 2022 climate disclosure rule?",
        "Which companies would be covered by SEC climate disclosure requirements?",
        "Has the SEC climate rule been finalized or is it still contested?",
    ],
    "tnfd": [
        "What does TNFD stand for and what does it ask companies to disclose?",
        "How is TNFD similar to TCFD in structure?",
        "Is TNFD mandatory or voluntary?",
    ],
    "sbti": [
        "What does it mean for a company to have a 'science-based target' under SBTi?",
        "What is the difference between a 1.5°C aligned target and a well-below 2°C target under SBTi?",
        "Can a company use carbon offsets to meet its SBTi target?",
    ],
    "gri": [
        "What is the GRI Universal Standards and what does it cover?",
        "Is GRI reporting mandatory for any companies?",
        "How does GRI relate to ESRS — are they compatible?",
    ],
    "california_climate": [
        "What does California SB 253 require companies to report?",
        "Which companies are covered by California's SB 253 climate law?",
        "How does California SB 261 differ from SB 253?",
    ],
    "double_materiality": [
        "What is the difference between impact materiality and financial materiality?",
        "Which EU regulation requires double materiality assessment?",
        "Does double materiality mean a topic must meet both tests to be reportable?",
    ],
}


def _load() -> list[dict]:
    if _MAP_FILE.exists():
        try:
            return json.loads(_MAP_FILE.read_text())
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
    """Return the highest-priority topic for the next learn session."""
    topics = get_map()
    # Prioritise: unknown first, then seed, then learning — lowest pct wins ties
    learnable = [t for t in topics if t["status"] not in ("functional", "mastered")]
    if not learnable:
        return None
    learnable.sort(key=lambda t: (_STATUS_ORDER.index(t["status"]), t["pct"]))
    return learnable[0]


def get_next_question(topic_id: str) -> str | None:
    """Return the next unanswered question for a topic."""
    questions = _QUESTION_BANK.get(topic_id, [])
    topics = get_map()
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic or not questions:
        return None
    asked = topic.get("questions_asked", 0)
    if asked >= len(questions):
        return questions[-1]  # repeat last if exhausted
    return questions[asked]


def record_answer(topic_id: str, answer_text: str, reference: str = "") -> dict:
    """Record a user answer, advance question count, recalculate pct."""
    with _lock:
        topics = _load()
        for topic in topics:
            if topic["id"] == topic_id:
                topic["questions_asked"] = topic.get("questions_asked", 0) + 1
                topic["questions_answered"] = topic.get("questions_answered", 0) + 1
                topic["last_updated"] = datetime.now(timezone.utc).isoformat()
                # Advance pct and status based on answers
                topic["pct"] = min(100, topic["pct"] + 15)
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
