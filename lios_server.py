"""
LIOS Server — clean standalone FastAPI backend.

Start: uvicorn lios_server:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
  GET  /health
  GET  /brain/status          Brain on/off, LLM reachable, knowledge count
  POST /brain/toggle          { "enabled": true/false }
  POST /chat                  { "query", "session_id", "messages"? }
  GET  /chat/history/{sid}    Recent chat turns for a session
  POST /feedback              { "session_id", "message_id", "feedback_type", "correction_text", "make_rule" }
  GET  /memory/corrections    List corrections
  GET  /memory/rules          List active rules
  POST /memory/rules          { "rule_text", "topic"? }
  DELETE /memory/rules/{id}   Deactivate a rule
  GET  /learn/next            Next question LIOS will ask you
  POST /learn/answer          { "topic_id", "answer_text", "reference"? }
  GET  /learn/map             Full knowledge map with % per topic
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lios.memory import brain_state, knowledge_map, store
from lios.memory.llm_client import chat as llm_chat, generate_learn_question

app = FastAPI(title="LIOS Brain Server", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_CHAT_LOG = Path("logs/server_chat.jsonl")
_CHAT_LOG.parent.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_chat(entry: dict) -> None:
    with _CHAT_LOG.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_session(session_id: str, limit: int = 30) -> list[dict]:
    if not _CHAT_LOG.exists():
        return []
    rows = []
    for line in _CHAT_LOG.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if row.get("session_id") == session_id:
                rows.append(row)
        except Exception:
            pass
    return rows[-limit:]


def _session_messages(session_id: str) -> list[dict[str, str]]:
    """Return OpenAI-format messages for last N turns of a session."""
    turns = _load_session(session_id, limit=10)
    msgs = []
    for t in turns:
        msgs.append({"role": "user", "content": t.get("query", "")})
        msgs.append({"role": "assistant", "content": t.get("answer", "")})
    return msgs


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "LIOS Brain Server", "version": "2.0.0"}


# ── Brain ─────────────────────────────────────────────────────────────────────

@app.get("/brain/status")
def brain_status() -> dict:
    state = brain_state.get_state()
    reachable = brain_state.check_llm_reachable()
    chunks = brain_state.get_knowledge_chunk_count()
    rules = store.list_rules(active_only=True)
    corrections = store.list_corrections(limit=1000)
    return {
        "brain_on": state.get("enabled", True),
        "model": state.get("model", "mistral"),
        "base_url": state.get("base_url", "http://localhost:11434"),
        "llm_reachable": reachable,
        "knowledge_chunks": chunks,
        "active_rules": len(rules),
        "total_corrections": len(corrections),
        "toggled_at": state.get("toggled_at"),
    }


class BrainToggleRequest(BaseModel):
    enabled: bool


@app.post("/brain/toggle")
def brain_toggle(body: BrainToggleRequest) -> dict:
    state = brain_state.set_enabled(body.enabled)
    return {
        "brain_on": state["enabled"],
        "model": state.get("model", "mistral"),
        "toggled_at": state.get("toggled_at"),
    }


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"
    messages: list[dict[str, str]] | None = None  # optional history override


@app.post("/chat")
def chat(body: ChatRequest) -> dict:
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")

    session_id = body.session_id or "default"
    history = body.messages if body.messages is not None else _session_messages(session_id)

    result = llm_chat(messages=history, query=body.query, session_id=session_id)

    message_id = str(uuid.uuid4())[:8]
    turn = {
        "message_id": message_id,
        "session_id": session_id,
        "timestamp": _now(),
        "query": body.query,
        "answer": result["answer"],
        "confidence": result.get("confidence", "medium"),
        "source": result.get("source", "unknown"),
        "brain_used": result.get("brain_used", False),
        "feedback": None,
    }
    _append_chat(turn)

    return {
        "message_id": message_id,
        "answer": result["answer"],
        "confidence": result.get("confidence", "medium"),
        "source": result.get("source", "unknown"),
        "brain_used": result.get("brain_used", False),
    }


@app.get("/chat/history/{session_id}")
def chat_history(session_id: str, limit: int = 20) -> dict:
    turns = _load_session(session_id, limit=limit)
    return {"session_id": session_id, "turns": turns}


# ── Feedback ──────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    session_id: str
    message_id: str
    query: str
    original_answer: str
    feedback_type: str                   # "good" | "wrong" | "partial"
    correction_text: str = ""
    make_rule: bool = False


@app.post("/feedback")
def submit_feedback(body: FeedbackRequest) -> dict:
    if body.feedback_type not in ("good", "wrong", "partial"):
        raise HTTPException(status_code=400, detail="feedback_type must be good/wrong/partial")

    if body.feedback_type == "good":
        # Just log it — nothing to store as a correction
        return {"stored": True, "rule_created": False, "message": "Confirmed as good answer"}

    if not body.correction_text.strip():
        raise HTTPException(status_code=400, detail="correction_text required for wrong/partial feedback")

    entry = store.add_correction(
        session_id=body.session_id,
        user_query=body.query,
        original_answer=body.original_answer,
        feedback_type=body.feedback_type,
        correction_text=body.correction_text,
        make_rule=body.make_rule,
    )
    return {
        "stored": True,
        "correction_id": entry["id"],
        "rule_created": body.make_rule,
        "message": "Correction stored" + (" and added as permanent rule" if body.make_rule else ""),
    }


# ── Memory — Corrections ──────────────────────────────────────────────────────

@app.get("/memory/corrections")
def list_corrections(limit: int = 50) -> dict:
    corrections = store.list_corrections(limit=limit)
    return {"corrections": corrections, "total": len(corrections)}


# ── Memory — Rules ────────────────────────────────────────────────────────────

class AddRuleRequest(BaseModel):
    rule_text: str
    topic: str = "general"


@app.get("/memory/rules")
def list_rules() -> dict:
    rules = store.list_rules(active_only=True)
    return {"rules": rules, "total": len(rules)}


@app.post("/memory/rules")
def add_rule(body: AddRuleRequest) -> dict:
    if not body.rule_text.strip():
        raise HTTPException(status_code=400, detail="rule_text cannot be empty")
    rule = store.add_rule(rule_text=body.rule_text, topic=body.topic, source="user")
    return {"created": True, "rule": rule}


@app.delete("/memory/rules/{rule_id}")
def deactivate_rule(rule_id: str) -> dict:
    removed = store.deactivate_rule(rule_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"deactivated": True, "rule_id": rule_id}


# ── Learn Mode ────────────────────────────────────────────────────────────────

@app.get("/learn/next")
def learn_next() -> dict:
    topic = knowledge_map.get_next_learn_topic()
    if not topic:
        return {
            "all_mastered": True,
            "message": "All topics are functional or mastered. Impressive.",
            "topic": None,
            "question": None,
        }

    # Try prebuilt question bank first; fall back to LLM-generated
    question = knowledge_map.get_next_question(topic["id"])
    if not question:
        question = generate_learn_question(
            topic_name=topic["name"],
            topic_desc=topic["description"],
            existing_pct=topic["pct"],
        )

    return {
        "all_mastered": False,
        "topic": {
            "id": topic["id"],
            "name": topic["name"],
            "category": topic["category"],
            "status": topic["status"],
            "pct": topic["pct"],
            "description": topic["description"],
        },
        "question": question,
    }


class LearnAnswerRequest(BaseModel):
    topic_id: str
    answer_text: str
    reference: str = ""


@app.post("/learn/answer")
def learn_answer(body: LearnAnswerRequest) -> dict:
    if not body.answer_text.strip():
        raise HTTPException(status_code=400, detail="answer_text cannot be empty")

    updated = knowledge_map.record_answer(
        topic_id=body.topic_id,
        answer_text=body.answer_text,
        reference=body.reference,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Store the answer as a verified knowledge correction
    store.add_correction(
        session_id="learn_mode",
        user_query=f"[LEARN] {updated.get('name', body.topic_id)}",
        original_answer="",
        feedback_type="partial",
        correction_text=body.answer_text + (f" (Reference: {body.reference})" if body.reference else ""),
        make_rule=False,
    )

    next_topic = knowledge_map.get_next_learn_topic()
    return {
        "topic_updated": {
            "id": updated["id"],
            "name": updated["name"],
            "pct": updated["pct"],
            "status": updated["status"],
        },
        "overall_pct": knowledge_map.get_overall_pct(),
        "next_topic": next_topic["name"] if next_topic else None,
    }


# ── Knowledge Map ─────────────────────────────────────────────────────────────

@app.get("/learn/map")
def knowledge_map_view() -> dict:
    topics = knowledge_map.get_map()
    overall = knowledge_map.get_overall_pct()

    # Group by category
    categories: dict[str, list[dict]] = {}
    for topic in topics:
        cat = topic["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "id": topic["id"],
            "name": topic["name"],
            "status": topic["status"],
            "pct": topic["pct"],
            "last_updated": topic.get("last_updated"),
        })

    return {
        "overall_pct": overall,
        "total_topics": len(topics),
        "mastered": sum(1 for t in topics if t["status"] == "mastered"),
        "functional": sum(1 for t in topics if t["status"] == "functional"),
        "learning": sum(1 for t in topics if t["status"] == "learning"),
        "unknown": sum(1 for t in topics if t["status"] in ("unknown", "seed")),
        "categories": categories,
    }
