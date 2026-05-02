"""Learning API router for autonomous research loop.

Provides endpoints for the LIOS Learn Copilot to fetch questions and submit answers:
- GET /learn/next → fetch next learning question
- POST /learn/answer → submit researched answer
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lios.logging_setup import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/learn", tags=["learning"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class TopicInfo(BaseModel):
    id: str
    name: str
    category: str
    status: str  # "unknown", "learning", "mastered"
    pct: float  # progress percentage for this topic (0-100)


class LearnNextResponse(BaseModel):
    all_mastered: bool
    topic: TopicInfo
    question: str
    question_type: str  # "definition", "application", "comparison", etc.


class AnswerSubmitRequest(BaseModel):
    topic_id: str
    answer_text: str
    reference: str  # source URL or citation


class AnswerSubmitResponse(BaseModel):
    status: str  # "success" or "skipped"
    topic_id: str
    next_topic_name: str
    current_pct: float
    message: str


# ---------------------------------------------------------------------------
# Learning State (in-memory for demo; would be persisted in production)
# ---------------------------------------------------------------------------

_TOPIC_LIBRARY: list[dict[str, Any]] = [
    {
        "id": "csrd_scope",
        "name": "CSRD Reporting Requirements",
        "category": "EU Sustainability Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "Which companies fall under CSRD mandatory reporting?",
        "question_type": "definition",
    },
    {
        "id": "csrd_timeline",
        "name": "CSRD Reporting Timeline",
        "category": "EU Sustainability Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What are the CSRD reporting phase-in dates for different company groups?",
        "question_type": "timeline",
    },
    {
        "id": "esrs_double_materiality",
        "name": "ESRS Double Materiality",
        "category": "EU Sustainability Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What is the difference between financial and impact materiality in ESRS?",
        "question_type": "comparison",
    },
    {
        "id": "esrs_value_chain",
        "name": "ESRS Value Chain Reporting",
        "category": "EU Sustainability Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "How does the ESRS value-chain concept affect disclosure scope?",
        "question_type": "application",
    },
    {
        "id": "eu_taxonomy_aligned",
        "name": "EU Taxonomy Alignment",
        "category": "EU Sustainability Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What are the criteria for an economic activity to be EU Taxonomy aligned?",
        "question_type": "definition",
    },
    {
        "id": "eu_taxonomy_dnhs",
        "name": "EU Taxonomy DNSH Test",
        "category": "EU Sustainability Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What does the 'do no significant harm' condition require under the EU Taxonomy?",
        "question_type": "definition",
    },
    {
        "id": "sfdr_disclosure",
        "name": "SFDR Disclosure Requirements",
        "category": "EU Financial Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What are the three categories of SFDR disclosure requirements?",
        "question_type": "enumeration",
    },
    {
        "id": "sfdr_pai",
        "name": "SFDR Principal Adverse Impacts",
        "category": "EU Financial Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What is a principal adverse impact (PAI) statement under SFDR?",
        "question_type": "definition",
    },
    {
        "id": "mifid_suitability",
        "name": "MiFID II Suitability",
        "category": "EU Financial Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "When must an investment firm perform a suitability assessment under MiFID II?",
        "question_type": "application",
    },
    {
        "id": "ucits_key_investor",
        "name": "UCITS Investor Disclosure",
        "category": "EU Financial Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What information must UCITS funds disclose in the key investor document?",
        "question_type": "enumeration",
    },
    {
        "id": "dora_resilience",
        "name": "DORA Operational Resilience",
        "category": "EU Financial Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What are the three pillar categories of DORA operational resilience?",
        "question_type": "enumeration",
    },
    {
        "id": "aml_risk_assessment",
        "name": "AML Risk Assessment",
        "category": "EU Financial Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What are the core steps in an EU anti-money laundering risk assessment?",
        "question_type": "enumeration",
    },
    {
        "id": "gmbhg_share_capital",
        "name": "GmbHG Share Capital",
        "category": "German Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What is the minimum share capital required for a German GmbH?",
        "question_type": "definition",
    },
    {
        "id": "hgb_financial_statements",
        "name": "HGB Financial Statements",
        "category": "German Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What are the core financial statement obligations for German merchants under HGB?",
        "question_type": "enumeration",
    },
    {
        "id": "aktg_management_duties",
        "name": "AktG Management Duties",
        "category": "German Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What fiduciary duties do the management board and supervisory board owe under the AktG?",
        "question_type": "comparison",
    },
    {
        "id": "bgb_contract_formation",
        "name": "BGB Contract Formation",
        "category": "German Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "How is a contract formed under the German Civil Code (BGB)?",
        "question_type": "definition",
    },
    {
        "id": "stgb_breach_of_trust",
        "name": "StGB Breach of Trust",
        "category": "German Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What conduct is typically covered by breach of trust under StGB Section 266?",
        "question_type": "definition",
    },
    {
        "id": "gdpr_rights",
        "name": "GDPR Data Subject Rights",
        "category": "German Law / Privacy",
        "status": "unknown",
        "pct": 0.0,
        "question": "Name the eight primary data subject rights under GDPR.",
        "question_type": "enumeration",
    },
    {
        "id": "legal_sources_hierarchy",
        "name": "Hierarchy of Legal Sources",
        "category": "Legal Foundations",
        "status": "unknown",
        "pct": 0.0,
        "question": "What is the hierarchy between EU law, federal law, and subordinate regulations?",
        "question_type": "comparison",
    },
    {
        "id": "proportionality_test",
        "name": "Proportionality Principle",
        "category": "Legal Foundations",
        "status": "unknown",
        "pct": 0.0,
        "question": "What are the standard steps in a proportionality analysis?",
        "question_type": "enumeration",
    },
    {
        "id": "legal_personality",
        "name": "Legal Personality",
        "category": "Legal Foundations",
        "status": "unknown",
        "pct": 0.0,
        "question": "What distinguishes a legal person from a natural person?",
        "question_type": "definition",
    },
    {
        "id": "jurisdiction_territorial",
        "name": "Territorial Jurisdiction",
        "category": "Legal Foundations",
        "status": "unknown",
        "pct": 0.0,
        "question": "When does territorial jurisdiction apply in cross-border disputes?",
        "question_type": "application",
    },
    {
        "id": "fundamental_rights",
        "name": "Fundamental Rights Review",
        "category": "Legal Foundations",
        "status": "unknown",
        "pct": 0.0,
        "question": "How do fundamental rights constrain public authority action?",
        "question_type": "application",
    },
    {
        "id": "un_global_compact",
        "name": "UN Global Compact",
        "category": "Global Frameworks",
        "status": "unknown",
        "pct": 0.0,
        "question": "What are the four core areas of the UN Global Compact?",
        "question_type": "enumeration",
    },
    {
        "id": "oecd_guidelines",
        "name": "OECD Guidelines for Multinationals",
        "category": "Global Frameworks",
        "status": "unknown",
        "pct": 0.0,
        "question": "What obligations do the OECD Guidelines impose on multinational enterprises?",
        "question_type": "definition",
    },
    {
        "id": "ifrs_s1_s2",
        "name": "IFRS S1 and S2",
        "category": "Global Frameworks",
        "status": "unknown",
        "pct": 0.0,
        "question": "What is the distinction between IFRS S1 and IFRS S2?",
        "question_type": "comparison",
    },
    {
        "id": "gri_standards",
        "name": "GRI Sustainability Standards",
        "category": "Global Frameworks",
        "status": "unknown",
        "pct": 0.0,
        "question": "How do the GRI Standards differ from financial reporting standards?",
        "question_type": "comparison",
    },
    {
        "id": "undrr_sendai",
        "name": "Sendai Framework for Disaster Risk Reduction",
        "category": "Global Frameworks",
        "status": "unknown",
        "pct": 0.0,
        "question": "What is the purpose of the Sendai Framework?",
        "question_type": "definition",
    },
    {
        "id": "ai_act_scope",
        "name": "AI Act High-Risk Classification",
        "category": "EU Digital & Cyber Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "Which of the following is classified as high-risk under the AI Act?",
        "question_type": "classification",
    },
    {
        "id": "nis2_scope",
        "name": "NIS2 Entity Obligations",
        "category": "EU Digital & Cyber Law",
        "status": "unknown",
        "pct": 0.0,
        "question": "What triggers NIS2 essential entity status for a corporation?",
        "question_type": "application",
    },
]


def _build_learning_state() -> dict[str, Any]:
    topics = [
        {
            "id": item["id"],
            "name": item["name"],
            "category": item["category"],
            "status": item["status"],
            "pct": item["pct"],
        }
        for item in _TOPIC_LIBRARY
    ]
    return {
        "topics": topics,
        "questions": {item["id"]: item["question"] for item in _TOPIC_LIBRARY},
        "question_types": {item["id"]: item["question_type"] for item in _TOPIC_LIBRARY},
        "answers_submitted": 0,
    }


_LEARNING_STATE = _build_learning_state()


def _find_topic(topics: list[dict[str, Any]], topic_id: str) -> dict[str, Any] | None:
    for topic in topics:
        if topic["id"] == topic_id:
            return topic
    return None


def _next_active_topic(topics: list[dict[str, Any]]) -> dict[str, Any] | None:
    active_topics = [topic for topic in topics if topic["pct"] < 90.0]
    if not active_topics:
        return None
    return min(active_topics, key=lambda topic: (topic["pct"], topic["category"], topic["name"]))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/next")
async def get_next_question() -> LearnNextResponse:
    """Fetch the next learning question.
    
    Returns the current topic's question. If all topics are mastered (pct >= 90),
    returns all_mastered=true.
    
    Increments topic index on each call to cycle through topics.
    """
    state = _LEARNING_STATE
    topics = state["topics"]
    question_map = state["questions"]
    question_type_map = state["question_types"]

    all_mastered = all(topic["pct"] >= 90.0 for topic in topics)

    if all_mastered:
        return LearnNextResponse(
            all_mastered=True,
            topic=TopicInfo(
                id="",
                name="All topics mastered!",
                category="",
                status="mastered",
                pct=100.0,
            ),
            question="",
            question_type="",
        )
    
    current_topic = _next_active_topic(topics)
    if current_topic is None:
        return LearnNextResponse(
            all_mastered=True,
            topic=TopicInfo(
                id="",
                name="All topics mastered!",
                category="",
                status="mastered",
                pct=100.0,
            ),
            question="",
            question_type="",
        )

    topic_id = current_topic["id"]

    response = LearnNextResponse(
        all_mastered=False,
        topic=TopicInfo(**current_topic),
        question=question_map.get(topic_id, ""),
        question_type=question_type_map.get(topic_id, "definition"),
    )

    return response


@router.post("/answer")
async def submit_answer(payload: AnswerSubmitRequest) -> AnswerSubmitResponse:
    """Submit a researched answer for a learning question.
    
    Validates the answer (ignores short answers as insufficient source).
    Updates progress on the topic (based on answer length as proxy for quality).
    Returns updated topic progress and next topic name.
    """
    state = _LEARNING_STATE
    topics = state["topics"]

    topic = _find_topic(topics, payload.topic_id)

    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic {payload.topic_id} not found")
    
    # Skip if answer is insufficient (too short or contains INSUFFICIENT_SOURCE marker)
    if (
        len(payload.answer_text.strip()) < 50
        or "INSUFFICIENT_SOURCE" in payload.answer_text
    ):
        logger.info(
            f"Skipped answer for topic {payload.topic_id}: insufficient source or short answer"
        )
        next_topic = _next_active_topic([candidate for candidate in topics if candidate["id"] != topic["id"]])
        return AnswerSubmitResponse(
            status="skipped",
            topic_id=payload.topic_id,
            next_topic_name=next_topic["name"] if next_topic else topic["name"],
            current_pct=topic["pct"],
            message="Answer skipped (insufficient source or too short)",
        )
    
    # Score answer based on length and reference presence (simple heuristic)
    # In production, would call an LLM or fact-check service
    base_score = min(30.0, len(payload.answer_text) / 20.0)  # up to 30 points for length
    reference_bonus = 15.0 if payload.reference and len(payload.reference.strip()) > 0 else 0.0
    increment = base_score + reference_bonus
    
    # Update topic progress
    old_pct = topic["pct"]
    topic["pct"] = min(100.0, topic["pct"] + increment)
    
    if topic["pct"] >= 90.0:
        topic["status"] = "mastered"
    elif topic["pct"] >= 50.0:
        topic["status"] = "learning"
    else:
        topic["status"] = "unknown"
    
    state["answers_submitted"] += 1
    
    next_topic = _next_active_topic([candidate for candidate in topics if candidate["id"] != topic["id"]])
    
    logger.info(
        f"Answer submitted for {payload.topic_id}: {old_pct:.1f}% → {topic['pct']:.1f}%"
    )
    
    return AnswerSubmitResponse(
        status="success",
        topic_id=payload.topic_id,
        next_topic_name=next_topic["name"] if next_topic else topic["name"],
        current_pct=topic["pct"],
        message=f"Answer recorded. {payload.topic_id} progress: {old_pct:.1f}% → {topic['pct']:.1f}%",
    )


@router.get("/status")
async def get_learning_status() -> dict[str, Any]:
    """Get current learning progress across all topics."""
    state = _LEARNING_STATE
    topics = state["topics"]
    
    return {
        "answers_submitted": state["answers_submitted"],
        "topics": topics,
        "scores": {t["id"]: t["pct"] for t in topics},
        "all_mastered": all(t["pct"] >= 90.0 for t in topics),
        "avg_progress": sum(t["pct"] for t in topics) / len(topics) if topics else 0.0,
    }
