"""FastAPI application – assembles all sub-routers with CORS and auth middleware."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel

from lios.api.routers import carbon, chat, core, dashboard, impact, supply_chain
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
app.include_router(carbon.router)
app.include_router(supply_chain.router)
app.include_router(impact.router)
app.include_router(dashboard.router)

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
    if context:
        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{user_query}\n\nANSWER:"
    else:
        prompt = f"QUESTION:\n{user_query}\n\nANSWER:"

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
