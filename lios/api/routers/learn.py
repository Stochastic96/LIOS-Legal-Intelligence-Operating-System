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

_LEARNING_STATE = {
    "topic_index": 0,
    "topics": [
        {
            "id": "csrd_scope",
            "name": "CSRD Reporting Requirements",
            "category": "EU Law",
            "status": "unknown",
            "pct": 0.0,
        },
        {
            "id": "esrs_double_materiality",
            "name": "ESRS Double Materiality",
            "category": "Sustainability",
            "status": "unknown",
            "pct": 0.0,
        },
        {
            "id": "eu_taxonomy_aligned",
            "name": "EU Taxonomy Alignment",
            "category": "Environmental",
            "status": "unknown",
            "pct": 0.0,
        },
        {
            "id": "sfdr_disclosure",
            "name": "SFDR Disclosure Requirements",
            "category": "Finance",
            "status": "unknown",
            "pct": 0.0,
        },
        {
            "id": "gdpr_rights",
            "name": "GDPR Data Subject Rights",
            "category": "Privacy",
            "status": "unknown",
            "pct": 0.0,
        },
        {
            "id": "dora_resilience",
            "name": "DORA Operational Resilience",
            "category": "Digital",
            "status": "unknown",
            "pct": 0.0,
        },
        {
            "id": "ai_act_scope",
            "name": "AI Act High-Risk Classification",
            "category": "AI",
            "status": "unknown",
            "pct": 0.0,
        },
        {
            "id": "nis2_scope",
            "name": "NIS2 Entity Obligations",
            "category": "Cybersecurity",
            "status": "unknown",
            "pct": 0.0,
        },
    ],
    "questions": {
        "csrd_scope": "Which companies fall under CSRD mandatory reporting?",
        "esrs_double_materiality": "What is the difference between financial and impact materiality in ESRS?",
        "eu_taxonomy_aligned": "What are the criteria for an economic activity to be EU Taxonomy aligned?",
        "sfdr_disclosure": "What are the three categories of SFDR disclosure requirements?",
        "gdpr_rights": "Name the eight primary data subject rights under GDPR.",
        "dora_resilience": "What are the three pillar categories of DORA operational resilience?",
        "ai_act_scope": "Which of the following is classified as high-risk under the AI Act?",
        "nis2_scope": "What triggers NIS2 essential entity status for a corporation?",
    },
    "question_types": {
        "csrd_scope": "definition",
        "esrs_double_materiality": "comparison",
        "eu_taxonomy_aligned": "definition",
        "sfdr_disclosure": "enumeration",
        "gdpr_rights": "enumeration",
        "dora_resilience": "enumeration",
        "ai_act_scope": "classification",
        "nis2_scope": "application",
    },
    "answers_submitted": 0,
}


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
    idx = state["topic_index"]
    
    # Check if all topics mastered (pct >= 90)
    all_mastered = all(t["pct"] >= 90.0 for t in topics)
    
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
    
    # Get current topic (cycle if needed)
    current_topic = topics[idx % len(topics)]
    topic_id = current_topic["id"]
    
    response = LearnNextResponse(
        all_mastered=False,
        topic=TopicInfo(**current_topic),
        question=question_map.get(topic_id, ""),
        question_type=question_type_map.get(topic_id, "definition"),
    )
    
    # Move to next topic for next call
    state["topic_index"] = (idx + 1) % len(topics)
    
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
    
    # Find the topic by ID
    topic = None
    for t in topics:
        if t["id"] == payload.topic_id:
            topic = t
            break
    
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
        return AnswerSubmitResponse(
            status="skipped",
            topic_id=payload.topic_id,
            next_topic_name=topics[(topics.index(topic) + 1) % len(topics)]["name"],
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
    
    # Get next topic
    current_idx = topics.index(topic)
    next_topic = topics[(current_idx + 1) % len(topics)]
    
    logger.info(
        f"Answer submitted for {payload.topic_id}: {old_pct:.1f}% → {topic['pct']:.1f}%"
    )
    
    return AnswerSubmitResponse(
        status="success",
        topic_id=payload.topic_id,
        next_topic_name=next_topic["name"],
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
