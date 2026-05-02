"""Chat UI and chat API routes."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from lios.api.dependencies import (
    engine,
    require_api_key,
    training_store,
    learning_event_store,
    feedback_handler,
    gap_detector,
    ai_activity_logger,
)
from lios.features.chat_training import ChatTurn, LocalTrainingStore
from lios.logging_setup import get_logger
from lios.models.validation import (
    ChatMessageRequest,
    FeedbackRequest,
    NextQuestionResponse,
    LearnStatusResponse,
    SessionSummaryResponse,
)
from lios.learning.feedback_handler import FeedbackEvent, FeedbackType
from lios.learning.learning_event_store import LearningEvent


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


# ---------------------------------------------------------------------------
# Learn Mode Endpoints (Feedback & Learning)
# ---------------------------------------------------------------------------


@router.post("/chat/api/feedback", dependencies=[Depends(require_api_key)])
async def submit_feedback(payload: FeedbackRequest) -> dict[str, Any]:
    """Submit feedback on a chat answer to train the learning system.
    
    Records user feedback (correct/incorrect/partial) and optional corrections
    to improve the knowledge base and detect learning gaps.
    """
    try:
        # Log the feedback submission to AI activity log
        ai_activity_logger.log(
            actor="feedback_handler",
            action="feedback_submission",
            description=f"Feedback type: {payload.response}",
            affected_files=["logs/learning_events.db"],
            metadata={
                "session_id": payload.session_id,
                "turn_id": payload.turn_id,
                "response_type": payload.response,
                "has_correction": payload.correction is not None,
            },
        )

        # Map feedback response to FeedbackType enum
        feedback_type_map = {
            "correct": FeedbackType.VERIFIED,
            "incorrect": FeedbackType.WRONG,
            "partially_correct": FeedbackType.PARTIAL,
            "unclear": FeedbackType.PARTIAL,
        }
        feedback_type = feedback_type_map.get(payload.response, FeedbackType.PARTIAL)

        # Create and process feedback event
        feedback_event = FeedbackEvent.create(
            session_id=payload.session_id,
            query="",  # Could be retrieved from session history
            answer="",  # Could be retrieved from session history
            feedback_type=feedback_type,
            feedback_text=payload.feedback_text or payload.correction,
            user_id=None,
            confidence_before=payload.confidence_level,
        )

        # Process feedback through handler
        result = feedback_handler.process_feedback(feedback_event)

        logger.info(
            f"Feedback processed for session {payload.session_id}: "
            f"response={payload.response}, feedback_id={result.get('feedback_id', 'N/A')}"
        )

        return {
            "status": "success",
            "session_id": payload.session_id,
            "feedback_id": result.get("feedback_id"),
            "message": "Feedback recorded and integrated into learning system",
        }

    except Exception as e:
        logger.error(f"Error processing feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to process feedback", "details": str(e)},
        )


@router.get("/chat/api/next-question", dependencies=[Depends(require_api_key)])
async def get_next_question(session_id: str) -> NextQuestionResponse:
    """Get the next recommended learning question based on detected gaps.
    
    Analyzes session history and learning events to identify knowledge gaps,
    then recommends the next question to help close those gaps.
    """
    try:
        if not session_id.strip():
            raise HTTPException(status_code=400, detail={"error": "session_id is required"})

        # Log the request to AI activity log
        ai_activity_logger.log(
            actor="gap_detector",
            action="next_question_request",
            description=f"Generated next learning question for session {session_id}",
            metadata={"session_id": session_id},
        )

        # Get next question from gap detector (returns tuple of (topic_name, question_text))
        topic_name, question = gap_detector.get_next_question()

        if not question:
            # Fallback if no gaps detected
            return NextQuestionResponse(
                session_id=session_id,
                question="What are the key differences between financial and non-financial materiality in CSRD?",
                topic="CSRD",
                difficulty_level="intermediate",
                explanation="Foundational materiality assessment question",
            )

        return NextQuestionResponse(
            session_id=session_id,
            question=question,
            topic=topic_name or "General",
            difficulty_level="intermediate",
            explanation=f"Recommended learning question on {topic_name}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting next question: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to generate next question", "details": str(e)},
        )


@router.get("/chat/api/learn-status", dependencies=[Depends(require_api_key)])
async def get_learn_status(session_id: str) -> LearnStatusResponse:
    """Get the current learning status and knowledge gap analysis for a session.
    
    Returns accuracy metrics, topics covered, and identified knowledge gaps
    to help track learning progress.
    """
    try:
        if not session_id.strip():
            raise HTTPException(status_code=400, detail={"error": "session_id is required"})

        # Log the request
        ai_activity_logger.log(
            actor="gap_detector",
            action="learn_status_request",
            description=f"Retrieved learning status for session {session_id}",
            metadata={"session_id": session_id},
        )

        # Get session feedback summary
        feedback_summary = feedback_handler.get_session_feedback(session_id)
        total_feedback = len(feedback_summary.get("feedback_events", []))
        correct_count = sum(
            1 for f in feedback_summary.get("feedback_events", [])
            if f.get("feedback_type") in ["verified", "correct"]
        )

        accuracy = (correct_count / total_feedback) if total_feedback > 0 else 0.0

        # Get knowledge gaps from gap detector
        knowledge_map = gap_detector.get_knowledge_map_status()
        gap_list = [
            {
                "topic": topic,
                "priority": "high" if info.get("gap_level") in ["unknown", "seed"] else "medium",
            }
            for topic, info in knowledge_map.items()
            if info.get("gap_level") != "mastered"
        ][:5]  # Top 5 gaps

        # Get session topics (from chat history)
        session_turns = training_store.list_session(session_id)
        topics_set = set()
        for turn in session_turns:
            if turn.get("intent"):
                topics_set.add(turn["intent"])

        return LearnStatusResponse(
            session_id=session_id,
            total_questions_answered=total_feedback,
            correct_answers=correct_count,
            accuracy=accuracy,
            topics_covered=list(topics_set),
            knowledge_gaps=gap_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting learn status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to retrieve learning status", "details": str(e)},
        )


@router.get("/chat/api/session-summary", dependencies=[Depends(require_api_key)])
async def get_session_summary(session_id: str) -> SessionSummaryResponse:
    """Get a comprehensive summary of a learning session with metrics and recommendations.
    
    Includes chat turn counts, feedback statistics, confidence metrics,
    and recommended next steps for continued learning.
    """
    try:
        if not session_id.strip():
            raise HTTPException(status_code=400, detail={"error": "session_id is required"})

        # Log the request
        ai_activity_logger.log(
            actor="session_manager",
            action="session_summary_request",
            description=f"Generated summary for session {session_id}",
            metadata={"session_id": session_id},
        )

        # Get session turns
        session_turns = training_store.list_session(session_id)
        total_turns = len(session_turns)

        # Calculate duration (if timestamps available)
        duration_seconds = 0
        if total_turns > 1:
            # Simple heuristic: 5 minutes per turn on average
            duration_seconds = total_turns * 300

        # Get feedback summary
        feedback_summary = feedback_handler.get_session_feedback(session_id)
        feedback_events = feedback_summary.get("feedback_events", [])

        # Count feedback types
        feedback_counts = {}
        confidence_before = []
        confidence_after = []

        for event in feedback_events:
            ftype = event.get("feedback_type", "unknown")
            feedback_counts[ftype] = feedback_counts.get(ftype, 0) + 1
            if event.get("confidence_before"):
                confidence_before.append(event["confidence_before"])
            if event.get("confidence_after"):
                confidence_after.append(event["confidence_after"])

        avg_conf_before = sum(confidence_before) / len(confidence_before) if confidence_before else 0.0
        avg_conf_after = sum(confidence_after) / len(confidence_after) if confidence_after else 0.0
        conf_improvement = avg_conf_after - avg_conf_before

        # Get learning events
        try:
            knowledge_map = gap_detector.get_knowledge_map_status()
            key_events = [
                {
                    "event_type": "gap_detection",
                    "topic": topic,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                for topic, info in knowledge_map.items()
                if info.get("gap_level") in ["unknown", "seed"]
            ][:5]  # Top 5 events
        except Exception:
            key_events = []

        # Get recommended next steps based on gaps
        learning_priorities = gap_detector.get_learning_priorities(limit=3)
        recommended_topics = [
            f"Review {gap.topic} - Increase from {gap.gap_level} level"
            for gap in learning_priorities
        ]

        return SessionSummaryResponse(
            session_id=session_id,
            total_turns=total_turns,
            duration_seconds=duration_seconds,
            feedback_collected=feedback_counts,
            confidence_metrics={
                "avg_confidence_before": round(avg_conf_before, 3),
                "avg_confidence_after": round(avg_conf_after, 3),
                "confidence_improvement": round(conf_improvement, 3),
            },
            key_learning_events=key_events,
            recommended_next_steps=recommended_topics,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating session summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to generate session summary", "details": str(e)},
        )

