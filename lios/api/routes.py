"""FastAPI application – assembles all sub-routers with CORS and auth middleware."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel

from lios.api.routers import carbon, chat, core, dashboard, impact, learn, supply_chain
from lios.config import settings
from lios.logging_setup import get_logger
from lios.models.validation import ErrorResponse
from lios.llm.ollama_client import call_ollama, check_ollama_health
from lios.retrieval.hybrid_retriever import get_retriever

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Legal Intelligence Operating System for EU sustainability compliance.",
)

# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with a structured response."""
    request_id = str(uuid.uuid4())
    logger.error(f"Validation error (request_id={request_id}): {exc}")
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="Request validation failed",
            error_type="validation",
            details={
                "errors": [
                    {
                        "field": ".".join(str(loc) for loc in error["loc"]),
                        "type": error["type"],
                        "message": error["msg"],
                    }
                    for error in exc.errors()
                ]
            },
            request_id=request_id,
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Health check – used by the mobile app Settings screen
# ---------------------------------------------------------------------------


@app.get("/health")
def health_check() -> dict[str, str]:
    """Simple liveness probe for the mobile app."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static utility routes
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect the base URL to the chat workspace."""
    return RedirectResponse(url="/chat", status_code=307)


@app.get("/chat-ui", include_in_schema=False)
def chat_ui_alias() -> RedirectResponse:
    """Alias /chat-ui → /chat for backwards compatibility."""
    return RedirectResponse(url="/chat", status_code=307)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Return an empty favicon response to suppress noisy 404 logs."""
    return Response(status_code=204)


@app.get("/debug/routes", include_in_schema=False)
def debug_routes() -> dict[str, list[str]]:
    """List registered routes.  Only accessible when ``LIOS_DEV_MODE=true``."""
    if not settings.DEV_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    paths = sorted({route.path for route in app.routes})
    return {"routes": paths}


# ---------------------------------------------------------------------------
# Include sub-routers
# ---------------------------------------------------------------------------

app.include_router(core.router)
app.include_router(chat.router)
app.include_router(learn.router)
app.include_router(carbon.router)
app.include_router(supply_chain.router)
app.include_router(impact.router)
app.include_router(dashboard.router)


# ---------------------------------------------------------------------------
# Startup health check
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def _startup_ollama_health_check() -> None:
    """Warn early if Ollama is unreachable or the configured model is missing."""
    if not settings.LLM_ENABLED:
        logger.info("LLM disabled (LIOS_LLM_ENABLED=false) – skipping Ollama health check.")
        return

    from lios.llm.ollama_client import OLLAMA_MODEL, check_ollama_health

    health = check_ollama_health()
    if not health["available"]:
        logger.warning(
            "Ollama is NOT reachable at %s. Start it with: ollama serve",
            settings.LLM_BASE_URL,
        )
        return

    available_models: list[str] = health.get("models", [])
    if OLLAMA_MODEL not in available_models:
        logger.warning(
            "Ollama is running but model %r is not pulled. "
            "Run: ollama pull %s   (available: %s)",
            OLLAMA_MODEL,
            OLLAMA_MODEL,
            available_models or "none",
        )

# ---------------------------------------------------------------------------
# Ollama status endpoint
# ---------------------------------------------------------------------------


@app.get("/api/ollama-status")
def ollama_status() -> dict[str, Any]:
    """Check Ollama availability and list available models.

    Returns JSON with ``available`` (bool) and ``models`` (list of model names).
    No API key required – safe to call from monitoring scripts.
    """
    return check_ollama_health()


# ---------------------------------------------------------------------------
# Direct RAG + Ollama query endpoint
# ---------------------------------------------------------------------------


class _RagQueryRequest(BaseModel):
    query: str


@app.post("/api/query")
async def rag_query(request: _RagQueryRequest) -> dict[str, Any]:
    """Process a legal query using BM25 retrieval and Ollama LLM.

    This endpoint always calls Ollama – it does not rely on the rule-based
    engine pipeline.  It is a clean end-to-end test of the full RAG path:
    BM25 retrieval → prompt construction → Ollama generate.

    Returns JSON with ``query``, ``answer``, and ``sources`` (list of dicts).
    """
    import asyncio

    retriever = get_retriever()
    user_query = request.query.strip()

    # Stage 1 – retrieve context (runs in executor to avoid blocking the event loop)
    def _search() -> list:
        return retriever.search(user_query, top_k=5)

    try:
        chunks = await asyncio.get_event_loop().run_in_executor(None, _search)
        context = retriever.format_context(chunks) if chunks else ""
    except Exception as exc:
        logger.warning("Retriever failed in /api/query: %s", exc)
        chunks = []
        context = ""

    # Stage 2 – build prompt
    from lios.reasoning.legal_reasoner import build_direct_prompt, build_prompt
    raw_chunks = [rc.chunk for rc in chunks]
    prompt = build_prompt(user_query, raw_chunks) if raw_chunks else build_direct_prompt(user_query)

    # Stage 3 – call Ollama asynchronously
    try:
        answer = await call_ollama(prompt)
    except Exception as exc:
        logger.error("Ollama call failed in /api/query: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error=f"Ollama is unavailable: {exc}",
                error_type="service_unavailable",
            ).model_dump(),
        )

    sources = [
        {
            "regulation": rc.chunk.get("regulation", ""),
            "article": rc.chunk.get("article", ""),
            "title": rc.chunk.get("title", ""),
            "score": round(rc.total_score, 4),
            "source_url": rc.chunk.get("source_url", ""),
        }
        for rc in chunks
    ]

    return {"query": user_query, "answer": answer, "sources": sources}


# ---------------------------------------------------------------------------
# Synthesize endpoint – uses AnswerSynthesizer without requiring Ollama
# ---------------------------------------------------------------------------


class _SynthesizeRequest(BaseModel):
    query: str


@app.post("/api/synthesize")
def synthesize_answer(request: _SynthesizeRequest) -> dict[str, Any]:
    """Synthesize a dynamic IRAC answer using the retrieval corpus (no Ollama required).

    Unlike ``/api/query`` this endpoint never calls Ollama.  It uses
    :class:`~lios.intelligence.answer_synthesizer.AnswerSynthesizer` to build
    a structured IRAC answer directly from retrieved legal chunks.  This
    ensures an answer is always available even when Ollama is offline.

    Returns JSON with ``query``, ``answer``, ``question_type``, and ``sources``.
    """
    from lios.intelligence.answer_synthesizer import AnswerSynthesizer
    from lios.intelligence.question_classifier import QuestionClassifier

    retriever = get_retriever()
    user_query = request.query.strip()

    retrieved = retriever.search(user_query, top_k=5)
    chunks = [rc.chunk for rc in retrieved]

    classifier = QuestionClassifier()
    question_type = classifier.classify(user_query).value

    synthesizer = AnswerSynthesizer()
    answer = synthesizer.synthesize(user_query, chunks)

    sources = [
        {
            "regulation": rc.chunk.get("regulation", ""),
            "article": rc.chunk.get("article", ""),
            "title": rc.chunk.get("title", ""),
            "score": round(rc.total_score, 4),
            "source_url": rc.chunk.get("source_url", ""),
        }
        for rc in retrieved
    ]

    return {
        "query": user_query,
        "answer": answer,
        "question_type": question_type,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Feedback endpoint – mobile app sends thumbs up/down + optional correction
# ---------------------------------------------------------------------------


class _FeedbackRequest(BaseModel):
    query: str
    answer: str
    feedback_type: str  # "positive", "negative", "partial"
    correction_text: str = ""
    session_id: str = ""


@app.post("/api/feedback")
def submit_feedback(request: _FeedbackRequest) -> dict[str, Any]:
    """Accept a feedback/correction from the mobile app and persist it.

    Stores the entry in ``data/memory/corrections.json`` using the same
    schema as the existing correction records so the LIOS learning pipeline
    can consume it without changes.

    Returns JSON with ``status`` and the assigned correction ``id``.
    """
    import json
    from datetime import datetime, timezone
    from pathlib import Path

    corrections_path = Path(__file__).parent.parent.parent / "data" / "memory" / "corrections.json"

    try:
        existing = json.loads(corrections_path.read_text(encoding="utf-8")) if corrections_path.exists() else []
    except Exception:
        existing = []

    new_id = f"corr-{len(existing) + 1:04d}"
    entry = {
        "id": new_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": request.session_id or "mobile",
        "user_query": request.query,
        "original_answer": request.answer,
        "feedback_type": request.feedback_type,
        "correction_text": request.correction_text,
        "made_rule": False,
        "source": "mobile_app",
    }

    existing.append(entry)
    corrections_path.write_text(json.dumps(existing, ensure_ascii=False, indent=4), encoding="utf-8")
    logger.info("Mobile feedback saved: %s (%s)", new_id, request.feedback_type)

    return {"status": "saved", "id": new_id}


# ---------------------------------------------------------------------------
# Evaluate endpoint – scores an answer against retrieved chunks
# ---------------------------------------------------------------------------


class _EvaluateRequest(BaseModel):
    question: str
    answer: str


@app.post("/api/evaluate")
def evaluate_answer(request: _EvaluateRequest) -> dict[str, Any]:
    """Evaluate the quality of a generated answer against the knowledge corpus.

    Retrieves relevant chunks for *question*, then scores *answer* on four
    dimensions: grounding, citation coverage, completeness, and diversity.

    Returns JSON with ``overall_score``, ``grade``, per-dimension scores,
    and ``feedback`` suggestions.
    """
    from lios.evaluation.answer_evaluator import AnswerEvaluator

    retriever = get_retriever()
    user_query = request.question.strip()

    retrieved = retriever.search(user_query, top_k=5)
    chunks = [rc.chunk for rc in retrieved]

    evaluator = AnswerEvaluator()
    result = evaluator.evaluate(
        question=user_query,
        answer=request.answer,
        chunks=chunks,
    )

    return {
        "question": user_query,
        "overall_score": result.overall_score,
        "grade": result.grade,
        "grounding_score": result.grounding_score,
        "citation_score": result.citation_score,
        "completeness_score": result.completeness_score,
        "diversity_score": result.diversity_score,
        "feedback": result.feedback,
    }

# ---------------------------------------------------------------------------
# Document upload endpoint – index uploaded files into the retrieval corpus
# ---------------------------------------------------------------------------


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    regulation: str = Form(default="CUSTOM"),
    source_description: str = Form(default=""),
) -> dict[str, Any]:
    """Upload a document (PDF, DOCX, or TXT) and index it into the retrieval corpus.

    The document is chunked, persisted to ``data/corpus/legal_chunks.jsonl``, and
    the HybridRetriever index is refreshed so new content is immediately searchable.

    Args:
        file:               The uploaded file (multipart/form-data).
        title:              Optional document title (defaults to filename).
        regulation:         Regulation or topic tag for the document (default: CUSTOM).
        source_description: Free-text description of the document source.

    Returns:
        JSON with ``status``, ``chunks_added``, and ``filename``.
    """
    from lios.ingestion.document_indexer import index_uploaded_document

    content = await file.read()
    filename = file.filename or "upload"
    content_type = file.content_type or ""

    result = index_uploaded_document(
        content=content,
        filename=filename,
        content_type=content_type,
        title=title or filename,
        regulation=regulation,
        source_description=source_description,
    )
    return result


# ---------------------------------------------------------------------------
# Mobile app endpoints — Brain, Chat alias, Feedback alias, Memory, LLM mode
# ---------------------------------------------------------------------------
#
# The Expo mobile client (lios-mobile/) calls paths like /brain/status, /chat,
# /memory/rules etc.  These thin endpoints translate to the existing engine and
# data files so the mobile app works without touching the core pipeline.
# ---------------------------------------------------------------------------

import json as _json
from datetime import datetime, timezone
from pathlib import Path

_BRAIN_STATE_PATH = Path("data/memory/brain_state.json")
_CORRECTIONS_PATH = Path("data/memory/corrections.json")
_RULES_PATH = Path("data/memory/rules.json")
_LOGS_PATH = Path("logs/chat_training.jsonl")


def _read_json(path: Path, default: Any) -> Any:
    try:
        return _json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")


def _brain_state() -> dict[str, Any]:
    return _read_json(_BRAIN_STATE_PATH, {"enabled": True, "model": "mistral", "base_url": "http://localhost:11434", "toggled_at": None})


def _llm_reachable() -> bool:
    try:
        from lios.llm.ollama_client import check_ollama_health
        return check_ollama_health().get("available", False)
    except Exception:
        return False


def _build_brain_status(state: dict[str, Any]) -> dict[str, Any]:
    from lios.llm.refiner import get_runtime_provider
    retriever = get_retriever()
    corrections = _read_json(_CORRECTIONS_PATH, [])
    rules = [r for r in _read_json(_RULES_PATH, []) if r.get("active", True)]
    provider = get_runtime_provider()
    model = state.get("model", "mistral")
    if provider == "groq":
        from lios.config import settings as _s
        model = _s.LLM_MODEL or "llama-3.3-70b-versatile"
    elif provider == "azure":
        from lios.config import settings as _s
        model = _s.AZURE_OPENAI_DEPLOYMENT or "gpt-4o"
    return {
        "brain_on": state.get("enabled", True),
        "model": model,
        "base_url": state.get("base_url", "http://localhost:11434"),
        "llm_reachable": _llm_reachable(),
        "knowledge_chunks": len(retriever._chunks) if retriever else 0,
        "active_rules": len(rules),
        "total_corrections": len(corrections),
        "toggled_at": state.get("toggled_at"),
    }


@app.get("/brain/status")
def brain_status() -> dict[str, Any]:
    """Brain status for the mobile app — LLM on/off, model, knowledge chunk count."""
    return _build_brain_status(_brain_state())


class _BrainToggleRequest(BaseModel):
    enabled: bool


@app.post("/brain/toggle")
def brain_toggle(request: _BrainToggleRequest) -> dict[str, Any]:
    """Enable or disable the LLM brain from the mobile app."""
    state = _brain_state()
    state["enabled"] = request.enabled
    state["toggled_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(_BRAIN_STATE_PATH, state)
    from lios.config import settings as _s
    _s.LLM_ENABLED = request.enabled
    return _build_brain_status(state)


# Chat alias — mobile sends to POST /chat (not /chat/api/message)

class _MobileChatRequest(BaseModel):
    query: str
    session_id: str = "mobile-session"
    messages: list[dict[str, str]] = []


@app.post("/chat")
def mobile_chat(request: _MobileChatRequest) -> dict[str, Any]:
    """Chat endpoint for the mobile app. Returns a mobile-shaped ChatResponse."""
    from lios.api.dependencies import engine as _engine
    import uuid as _uuid

    try:
        result = _engine.route_query(request.query)
        grounding = getattr(result, "grounding_score", 0.8)
        confidence_label = "high" if grounding >= 0.75 else "medium" if grounding >= 0.5 else "low"
        brain_state = _brain_state()
        return {
            "message_id": str(_uuid.uuid4()),
            "answer": result.answer,
            "confidence": confidence_label,
            "source": result.intent,
            "brain_used": brain_state.get("enabled", True),
        }
    except Exception as exc:
        logger.warning("mobile_chat error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/chat/history/{session_id}")
def mobile_chat_history(session_id: str, limit: int = 20) -> dict[str, Any]:
    """Return recent chat turns for a session (read from JSONL log)."""
    turns: list[dict[str, Any]] = []
    if _LOGS_PATH.exists():
        try:
            lines = _LOGS_PATH.read_text(encoding="utf-8").strip().splitlines()
            for line in reversed(lines):
                if not line.strip():
                    continue
                entry = _json.loads(line)
                if entry.get("session_id") == session_id:
                    turns.append(entry)
                if len(turns) >= limit:
                    break
        except Exception:
            pass
    return {"session_id": session_id, "turns": list(reversed(turns))}


# Feedback alias — mobile posts to /feedback (without /api/ prefix)

class _MobileFeedbackRequest(BaseModel):
    session_id: str = "mobile-session"
    message_id: str = ""
    query: str
    original_answer: str
    feedback_type: str  # "good" | "wrong" | "partial"
    correction_text: str = ""
    make_rule: bool = False


@app.post("/feedback")
def mobile_feedback(request: _MobileFeedbackRequest) -> dict[str, Any]:
    """Accept mobile feedback and persist it to corrections.json."""
    corrections = _read_json(_CORRECTIONS_PATH, [])
    new_id = f"corr-{len(corrections) + 1:04d}"
    entry = {
        "id": new_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "session_id": request.session_id,
        "user_query": request.query,
        "original_answer": request.original_answer,
        "feedback_type": request.feedback_type,
        "correction_text": request.correction_text,
        "made_rule": False,
        "source": "mobile_app",
    }
    corrections.append(entry)
    _write_json(_CORRECTIONS_PATH, corrections)

    rule_created = False
    if request.make_rule and request.correction_text.strip():
        rules = _read_json(_RULES_PATH, [])
        rule_id = f"rule-{len(rules) + 1:04d}"
        rules.append({
            "id": rule_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": request.session_id,
            "topic": "general",
            "rule_text": request.correction_text.strip(),
            "active": True,
        })
        _write_json(_RULES_PATH, rules)
        rule_created = True

    return {"stored": True, "rule_created": rule_created, "message": "Feedback saved"}


# Memory — corrections and rules CRUD

@app.get("/memory/corrections")
def memory_corrections(limit: int = 50) -> dict[str, Any]:
    """Return recent corrections from the mobile feedback store."""
    corrections = _read_json(_CORRECTIONS_PATH, [])
    subset = corrections[-limit:] if len(corrections) > limit else corrections
    return {"corrections": list(reversed(subset)), "total": len(corrections)}


@app.get("/memory/rules")
def memory_rules() -> dict[str, Any]:
    """Return all active rules."""
    rules = _read_json(_RULES_PATH, [])
    active = [r for r in rules if r.get("active", True)]
    return {"rules": active, "total": len(active)}


class _AddRuleRequest(BaseModel):
    rule_text: str
    topic: str = "general"


@app.post("/memory/rules")
def memory_add_rule(request: _AddRuleRequest) -> dict[str, Any]:
    """Add a persistent rule that is injected into every answer when brain is ON."""
    rules = _read_json(_RULES_PATH, [])
    rule_id = f"rule-{len(rules) + 1:04d}"
    rule = {
        "id": rule_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "mobile_app",
        "topic": request.topic,
        "rule_text": request.rule_text.strip(),
        "active": True,
    }
    rules.append(rule)
    _write_json(_RULES_PATH, rules)
    return {"created": True, "rule": rule}


@app.delete("/memory/rules/{rule_id}")
def memory_delete_rule(rule_id: str) -> dict[str, Any]:
    """Deactivate (soft-delete) a rule by ID."""
    rules = _read_json(_RULES_PATH, [])
    found = False
    for r in rules:
        if r["id"] == rule_id:
            r["active"] = False
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    _write_json(_RULES_PATH, rules)
    return {"deactivated": True}


# LLM mode switcher — lets the mobile app toggle between Local, Groq, Azure

_LLM_PRESETS: dict[str, dict[str, str]] = {
    "local": {
        "provider": "openai_compatible",
        "model": "mistral:latest",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "label": "Local (Ollama)",
    },
    "groq": {
        "provider": "openai_compatible",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": "",  # must be set via env LIOS_LLM_API_KEY or updated at runtime
        "label": "Groq (Fast / Free)",
    },
    "azure": {
        "provider": "azure",
        "model": "",  # comes from LIOS_AZURE_OPENAI_DEPLOYMENT
        "base_url": "",
        "api_key": "",
        "label": "Azure OpenAI (GPT-4)",
    },
}


@app.get("/api/llm-mode")
def get_llm_mode() -> dict[str, Any]:
    """Return the currently active LLM provider mode."""
    from lios.llm.refiner import get_runtime_provider
    from lios.config import settings as _s

    provider_key = get_runtime_provider()
    # Map internal provider string back to a mode label
    state = _brain_state()
    if provider_key == "azure":
        mode = "azure"
        model = _s.AZURE_OPENAI_DEPLOYMENT or "gpt-4o"
    elif _s.LLM_BASE_URL and "groq.com" in _s.LLM_BASE_URL:
        mode = "groq"
        model = _s.LLM_MODEL or "llama-3.3-70b-versatile"
    else:
        mode = "local"
        model = state.get("model", _s.LLM_MODEL or "mistral:latest")

    return {
        "mode": mode,
        "provider": provider_key,
        "model": model,
        "label": _LLM_PRESETS.get(mode, {}).get("label", mode),
        "reachable": _llm_reachable(),
    }


class _LLMModeRequest(BaseModel):
    mode: str  # "local" | "groq" | "azure"
    api_key: Optional[str] = None  # optional override (e.g. Groq key)


@app.get("/api/token-usage")
def token_usage_stats() -> dict[str, Any]:
    """Return cumulative LLM token usage and estimated cost.

    Use this to monitor how much of your Azure credit has been spent.
    """
    from lios.llm.token_budget import usage_summary
    return usage_summary()


@app.get("/api/training-export")
def training_export(limit: int = 500) -> dict[str, Any]:
    """Export chat history + corrections as Azure fine-tuning JSONL.

    Each accepted answer becomes a (system, user, assistant) training example.
    Corrections override the original assistant turn with the corrected text.

    Returns ``{ "samples": int, "jsonl": str }`` — save the jsonl string to a
    .jsonl file and upload to Azure AI Studio for fine-tuning.
    """
    import re

    corrections = _read_json(_CORRECTIONS_PATH, [])
    correction_map = {
        c["user_query"]: c["correction_text"]
        for c in corrections
        if c.get("correction_text") and c.get("feedback_type") in ("wrong", "partial")
    }

    lines: list[str] = []
    if _LOGS_PATH.exists():
        try:
            raw_lines = _LOGS_PATH.read_text(encoding="utf-8").strip().splitlines()
            for raw in raw_lines[-limit:]:
                if not raw.strip():
                    continue
                entry = _json.loads(raw)
                query = entry.get("query") or entry.get("user_query", "")
                answer = entry.get("answer") or entry.get("response", "")
                if not query or not answer:
                    continue
                # Use corrected answer if available
                final_answer = correction_map.get(query, answer)
                sample = {
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are LIOS, an EU sustainability regulation compliance advisor. "
                                "Answer questions about CSRD, ESRS, EU Taxonomy, SFDR, CS3D, and GDPR "
                                "accurately and concisely, citing article references."
                            ),
                        },
                        {"role": "user", "content": query},
                        {"role": "assistant", "content": final_answer},
                    ]
                }
                lines.append(_json.dumps(sample, ensure_ascii=False))
        except Exception as exc:
            logger.warning("training_export read error: %s", exc)

    return {"samples": len(lines), "jsonl": "\n".join(lines)}


@app.post("/api/llm-mode")
def set_llm_mode(request: _LLMModeRequest) -> dict[str, Any]:
    """Switch the active LLM provider at runtime without restarting the server.

    - ``local``  → Ollama on localhost (needs Ollama running)
    - ``groq``   → Groq cloud API (needs LIOS_LLM_API_KEY or api_key param)
    - ``azure``  → Azure OpenAI (needs LIOS_AZURE_OPENAI_* env vars)
    """
    from lios.llm.refiner import set_runtime_provider
    from lios.config import settings as _s

    mode = request.mode.lower()
    if mode not in _LLM_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown mode '{mode}'. Choose: local, groq, azure")

    preset = _LLM_PRESETS[mode]
    api_key = request.api_key or preset["api_key"] or _s.LLM_API_KEY
    set_runtime_provider(
        provider=preset["provider"],
        model=preset["model"] or _s.AZURE_OPENAI_DEPLOYMENT or _s.LLM_MODEL,
        base_url=preset["base_url"] or _s.LLM_BASE_URL,
        api_key=api_key,
    )

    # Persist the mode selection to brain_state.json
    state = _brain_state()
    state["active_mode"] = mode
    state["toggled_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(_BRAIN_STATE_PATH, state)

    logger.info("LLM mode switched to: %s", mode)
    return {"mode": mode, "label": preset["label"], "model": preset["model"] or _s.LLM_MODEL}


# ---------------------------------------------------------------------------
# Backward-compat re-exports used by existing tests
# ---------------------------------------------------------------------------
# Tests import shared singletons directly from this module.  Expose them so
# existing import paths keep working without modification.

from lios.api.dependencies import (  # noqa: E402  (after app is built)
    applicability_checker as _applicability_checker,
    carbon_engine as _carbon_engine,
    db as _db,
    engine as _engine,
    materiality_engine as _materiality_engine,
    roadmap_generator as _roadmap_generator,
    supply_chain_engine as _supply_chain_engine,
    training_store as _training_store,
)
