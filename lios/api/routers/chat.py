"""Chat UI and chat API routes."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from lios.api.dependencies import engine, require_api_key, training_store
from lios.features.chat_training import ChatTurn, LocalTrainingStore
from lios.logging_setup import get_logger
from lios.models.validation import ChatMessageRequest

logger = get_logger(__name__)

# Chat UI is public (no auth).  Chat API endpoints require auth when configured.
router = APIRouter()

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _read_template(name: str) -> str:
    path = _TEMPLATE_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"<html><body><p>Template '{name}' not found.</p></body></html>"


# ---------------------------------------------------------------------------
# Chat workspace UI
# ---------------------------------------------------------------------------

@router.get("/chat", response_class=HTMLResponse, include_in_schema=False)
def chat_workspace() -> str:
    """Serve the local-first visual chat workspace."""
    return _read_template("chat.html")


@router.get("/chat-react", response_class=HTMLResponse, include_in_schema=False)
def chat_workspace_react() -> str:
    """Serve the React-based chat workspace."""
    return _read_template("react_chat.html")


# ---------------------------------------------------------------------------
# Chat API (requires auth when configured)
# ---------------------------------------------------------------------------

@router.post("/chat/api/message", dependencies=[Depends(require_api_key)])
async def chat_message(payload: ChatMessageRequest) -> dict[str, Any]:
    """Process one chat message and persist the turn locally for training workflows."""
    import asyncio

    session_id = payload.session_id or str(uuid.uuid4())
    company_profile = payload.company_profile.model_dump() if payload.company_profile else None
    jurisdictions = payload.jurisdictions

    direction_hint = training_store.infer_session_direction(session_id=session_id, window=3)

    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: engine.route_query(
            query=payload.query,
            company_profile=company_profile,
            jurisdictions=jurisdictions,
            preferred_intent=(direction_hint or {}).get("intent"),
            preferred_regulation=(direction_hint or {}).get("regulation"),
            lightweight=None if company_profile else True,
            concise=True,
        ),
    )

    citation_rows = [
        {
            "regulation": c.regulation,
            "article_id": c.article_id,
            "title": c.title,
            "relevance_score": c.relevance_score,
            "url": c.url,
        }
        for c in result.citations
    ]

    training_store.append_turn(
        ChatTurn(
            timestamp=LocalTrainingStore.now_iso(),
            session_id=session_id,
            user_query=payload.query,
            answer=result.answer,
            intent=result.intent,
            citations=citation_rows,
            metadata={
                "consensus_reached": result.consensus_result.consensus_reached,
                "confidence": result.consensus_result.confidence,
                "direction_hint": direction_hint,
                "agent_count": len(result.consensus_result.agent_responses),
            },
        )
    )

    return {
        "session_id": session_id,
        "answer": result.answer,
        "intent": result.intent,
        "citations": citation_rows,
        "consensus": {
            "reached": result.consensus_result.consensus_reached,
            "confidence": result.consensus_result.confidence,
        },
        "mode": {
            "lightweight": (None if company_profile else True),
            "agent_count": len(result.consensus_result.agent_responses),
            "direction_hint": direction_hint,
        },
    }


@router.get("/chat/api/history", dependencies=[Depends(require_api_key)])
def chat_history(session_id: str) -> dict[str, Any]:
    """Load chat history for a local training session."""
    if not session_id.strip():
        raise HTTPException(status_code=400, detail={"error": "session_id is required"})
    return {"session_id": session_id, "turns": training_store.list_session(session_id)}


@router.get("/chat/api/export", dependencies=[Depends(require_api_key)])
def chat_export(session_id: str) -> HTMLResponse:
    """Export one session as JSONL suitable for prompt-tuning datasets."""
    if not session_id.strip():
        raise HTTPException(status_code=400, detail={"error": "session_id is required"})
    body = training_store.export_session_jsonl(session_id)
    return HTMLResponse(
        content=body,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f"attachment; filename={session_id}.jsonl"},
    )
