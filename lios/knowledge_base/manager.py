"""High-level Knowledge Base manager – coordinates ingestion and retrieval."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from lios.database.connection import AsyncSessionFactory
from lios.database.repositories.regulation_repo import RegulationORM, RegulationRepository
from lios.knowledge_base.indexing.vector_store import SearchResult, VectorStore
from lios.knowledge_base.ingestion.document_parser import DocumentParser
from lios.knowledge_base.ingestion.preprocessor import TextPreprocessor
from lios.knowledge_base.models import Framework, Regulation
from lios.utils.helpers import sha256_hex, utcnow
from lios.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBaseManager:
    """
    Facade for all KB operations:
    - ingest a new regulation (parse → chunk → embed → persist)
    - semantic search across regulations
    - list / delete regulations
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        parser: Optional[DocumentParser] = None,
        preprocessor: Optional[TextPreprocessor] = None,
    ) -> None:
        self._vs = vector_store or VectorStore()
        self._parser = parser or DocumentParser()
        self._preprocessor = preprocessor or TextPreprocessor()

    # ── Ingestion ─────────────────────────────────────────────────────────────
    async def ingest(
        self,
        title: str,
        short_name: str,
        framework: Framework,
        content: str,
        source_url: Optional[str] = None,
        published_at: Optional[datetime] = None,
        jurisdiction: str = "EU",
        version: str = "1.0",
    ) -> str:
        """
        Ingest a new regulation document.

        Returns the regulation ID.
        """
        regulation_id = sha256_hex(f"{short_name}:{version}:{title}")[:16]
        now = utcnow()

        # 1. Persist to SQLite
        async with AsyncSessionFactory() as session:
            repo = RegulationRepository(session)
            existing = await repo.get_by_id(regulation_id)
            if existing is None:
                orm = RegulationORM(
                    id=regulation_id,
                    title=title,
                    short_name=short_name,
                    framework=framework.value,
                    jurisdiction=jurisdiction,
                    content=content,
                    source_url=source_url,
                    published_at=published_at,
                    last_verified_at=now,
                    version=version,
                )
                await repo.create(orm)
                logger.info("Regulation '%s' saved to DB (id=%s)", short_name, regulation_id)
            else:
                logger.info("Regulation '%s' already in DB – skipping SQLite upsert", short_name)

        # 2. Chunk text
        chunks = self._preprocessor.chunk(regulation_id, content)

        # 3. Embed & upsert into vector store
        self._vs.add_chunks(
            chunk_ids=[c.chunk_id for c in chunks],
            texts=[c.text for c in chunks],
            metadatas=[
                {
                    "regulation_id": regulation_id,
                    "framework": framework.value,
                    "article_ref": c.article_ref or "",
                    "short_name": short_name,
                    "jurisdiction": jurisdiction,
                }
                for c in chunks
            ],
        )
        logger.info(
            "Ingested '%s' – %d chunks indexed in vector store", short_name, len(chunks)
        )
        return regulation_id

    # ── Retrieval ─────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = 5,
        framework_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Return semantically relevant chunks for *query*."""
        return self._vs.search(query, top_k=top_k, framework_filter=framework_filter)

    # ── Admin ─────────────────────────────────────────────────────────────────
    async def list_regulations(self) -> list[dict]:
        async with AsyncSessionFactory() as session:
            repo = RegulationRepository(session)
            rows = await repo.list_all()
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "short_name": r.short_name,
                    "framework": r.framework,
                    "jurisdiction": r.jurisdiction,
                    "version": r.version,
                    "last_verified_at": r.last_verified_at,
                }
                for r in rows
            ]

    async def delete_regulation(self, regulation_id: str) -> bool:
        async with AsyncSessionFactory() as session:
            repo = RegulationRepository(session)
            return await repo.delete(regulation_id)

    def stats(self) -> dict:
        return {"vector_chunks": self._vs.count()}
