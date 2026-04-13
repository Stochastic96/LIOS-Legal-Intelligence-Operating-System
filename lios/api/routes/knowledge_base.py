"""Knowledge base management endpoints."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from lios.knowledge_base.manager import KnowledgeBaseManager
from lios.knowledge_base.models import Framework

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

_manager = KnowledgeBaseManager()


class IngestRequest(BaseModel):
    title: str
    short_name: str
    framework: Framework
    content: str = Field(..., min_length=50)
    source_url: Optional[str] = None
    jurisdiction: str = "EU"
    version: str = "1.0"


@router.post("/ingest")
async def ingest_regulation(req: IngestRequest) -> dict[str, Any]:
    """Ingest a new regulation document into the knowledge base."""
    regulation_id = await _manager.ingest(
        title=req.title,
        short_name=req.short_name,
        framework=req.framework,
        content=req.content,
        source_url=req.source_url,
        jurisdiction=req.jurisdiction,
        version=req.version,
    )
    return {"status": "ingested", "regulation_id": regulation_id}


@router.get("/regulations")
async def list_regulations() -> dict[str, Any]:
    """List all regulations in the knowledge base."""
    regulations = await _manager.list_regulations()
    return {"count": len(regulations), "regulations": regulations}


@router.delete("/regulations/{regulation_id}")
async def delete_regulation(regulation_id: str) -> dict[str, Any]:
    """Remove a regulation from the knowledge base."""
    deleted = await _manager.delete_regulation(regulation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Regulation '{regulation_id}' not found.")
    return {"status": "deleted", "regulation_id": regulation_id}


@router.get("/stats")
async def kb_stats() -> dict[str, Any]:
    """Return knowledge base statistics."""
    return _manager.stats()


@router.get("/search")
async def search_kb(
    query: str,
    top_k: int = 5,
    framework: Optional[str] = None,
) -> dict[str, Any]:
    """Semantic search across the knowledge base."""
    results = _manager.search(query, top_k=top_k, framework_filter=framework)
    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "chunk_id": r.chunk_id,
                "regulation_id": r.regulation_id,
                "article_ref": r.article_ref,
                "text": r.text[:500],
                "score": r.score,
            }
            for r in results
        ],
    }
