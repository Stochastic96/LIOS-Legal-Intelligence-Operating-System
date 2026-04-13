"""ChromaDB-backed local vector store for regulation chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from lios.config import settings
from lios.knowledge_base.indexing.embedder import Embedder
from lios.utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "lios_regulations"


@dataclass
class SearchResult:
    chunk_id: str
    regulation_id: str
    article_ref: Optional[str]
    text: str
    score: float            # cosine similarity (0-1, higher = more relevant)
    metadata: dict[str, Any]


class VectorStore:
    """
    Thin wrapper around ChromaDB for storing and retrieving regulation chunks.

    All data is persisted locally at ``settings.vector_store_path``.
    """

    def __init__(self, embedder: Optional[Embedder] = None) -> None:
        self._embedder = embedder or Embedder()
        self._client = None   # lazy-loaded
        self._collection = None

    # ── Setup ─────────────────────────────────────────────────────────────────
    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        import chromadb  # lazy import

        self._client = chromadb.PersistentClient(
            path=str(settings.vector_store_path)
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Vector store ready – collection '%s' (%d docs)",
            COLLECTION_NAME,
            self._collection.count(),
        )
        return self._collection

    # ── Write ─────────────────────────────────────────────────────────────────
    def add_chunks(
        self,
        chunk_ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Embed *texts* and upsert into the collection."""
        if not texts:
            return
        embeddings = self._embedder.embed(texts).tolist()
        self._get_collection().upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.debug("Upserted %d chunks into vector store", len(texts))

    # ── Read ──────────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = 5,
        framework_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Return the *top_k* most relevant chunks for *query*."""
        query_embedding = self._embedder.embed_one(query).tolist()
        where = {"framework": framework_filter} if framework_filter else None

        results = self._get_collection().query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        output: list[SearchResult] = []
        for chunk_id, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append(
                SearchResult(
                    chunk_id=chunk_id,
                    regulation_id=meta.get("regulation_id", ""),
                    article_ref=meta.get("article_ref"),
                    text=doc,
                    score=1.0 - dist,  # cosine distance → similarity
                    metadata=meta,
                )
            )
        return output

    def count(self) -> int:
        return self._get_collection().count()

    def reset(self) -> None:
        """Delete and recreate the collection (use with caution)."""
        import chromadb  # lazy import

        self._client.delete_collection(COLLECTION_NAME)
        self._collection = None
        logger.warning("Vector store collection reset")
