"""Learning API router — LIOS Wissens-Copilot.

Endpoints:
  GET  /learn/next    — nächste Lernfrage abrufen
  POST /learn/answer  — Antwort einreichen
  GET  /learn/map     — Wissenskarte mit Kategorieübersicht
  GET  /learn/status  — Gesamtfortschritt
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lios.logging_setup import get_logger
from lios.memory import knowledge_map as km

logger = get_logger(__name__)

router = APIRouter(prefix="/learn", tags=["learning"])


# ── Request / Response Models ─────────────────────────────────────────────────

class AnswerSubmitRequest(BaseModel):
    topic_id: str
    answer_text: str
    reference: str = ""
    question_text: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/next")
async def get_next_question(include_mastered: bool = False) -> dict[str, Any]:
    """Nächste Lernfrage aus der persistenten Wissenskarte abrufen."""
    topic = km.get_next_learn_topic(include_mastered=include_mastered)
    if topic is None:
        return {"all_mastered": True, "topic": None, "question": None}
    q = km.get_next_question(topic["id"])
    return {
        "all_mastered": (not include_mastered) and topic.get("status") in ("functional", "mastered"),
        "topic": dict(topic),
        "question": q["q"] if q else None,
        "question_type": q.get("type") if q else None,
        "question_source": q.get("source") if q else None,
    }


@router.post("/answer")
async def submit_answer(payload: AnswerSubmitRequest) -> dict[str, Any]:
    """Antwort auf eine Lernfrage einreichen und Fortschritt aktualisieren."""
    topics = km.get_map()
    topic = next((t for t in topics if t["id"] == payload.topic_id), None)
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Thema {payload.topic_id} nicht gefunden")

    result  = km.record_answer(
        payload.topic_id,
        payload.answer_text,
        payload.reference,
        payload.question_text,
    )
    updated = result["topic"]

    logger.info(
        "Antwort für %s: %d%% → %d%%",
        payload.topic_id, topic["pct"], updated.get("pct", topic["pct"]),
    )

    return {
        "topic_updated": updated,
        "overall_pct":   result["overall_pct"],
        "next_topic":    result["next_topic"],
    }


@router.get("/map")
async def get_knowledge_map() -> dict[str, Any]:
    """Wissenskarte mit Kategorien und Fortschritt zurückgeben."""
    topics = km.get_map()

    by_cat: dict[str, list[dict]] = {}
    status_counts: dict[str, int] = {
        "mastered": 0, "functional": 0, "connected": 0,
        "learning": 0, "seed": 0, "unknown": 0,
    }

    for t in topics:
        cat = t.get("category", "Sonstige")
        by_cat.setdefault(cat, []).append(t)
        s = t.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "overall_pct":  km.get_overall_pct(),
        "total_topics": len(topics),
        "mastered":     status_counts["mastered"],
        "functional":   status_counts["functional"] + status_counts["connected"],
        "learning":     status_counts["learning"] + status_counts["seed"],
        "unknown":      status_counts["unknown"],
        "categories":   by_cat,
    }


@router.get("/status")
async def get_learning_status() -> dict[str, Any]:
    """Gesamtlernfortschritt über alle Themen."""
    topics = km.get_map()
    return {
        "topics":       topics,
        "scores":       {t["id"]: t["pct"] for t in topics},
        "all_mastered": all(t["pct"] >= 90 for t in topics),
        "avg_progress": round(sum(t["pct"] for t in topics) / len(topics)) if topics else 0,
    }
