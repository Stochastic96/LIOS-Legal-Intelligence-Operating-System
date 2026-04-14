"""Shared data models for ingestion and provenance-aware retrieval."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


@dataclass
class LegalChunk:
    """Canonical legal chunk with source provenance metadata."""

    chunk_id: str
    source_url: str
    celex_or_doc_id: str
    jurisdiction: str
    regulation: str
    article: str
    published_date: str
    effective_date: str
    version_hash: str
    ingestion_timestamp: str
    title: str
    text: str

    @classmethod
    def create(
        cls,
        *,
        source_url: str,
        celex_or_doc_id: str,
        jurisdiction: str,
        regulation: str,
        article: str,
        published_date: str,
        effective_date: str,
        title: str,
        text: str,
    ) -> "LegalChunk":
        raw = f"{celex_or_doc_id}|{regulation}|{article}|{title}|{text}".encode("utf-8")
        version_hash = sha256(raw).hexdigest()
        chunk_id = sha256(f"{regulation}:{article}:{version_hash}".encode("utf-8")).hexdigest()[:16]
        return cls(
            chunk_id=chunk_id,
            source_url=source_url,
            celex_or_doc_id=celex_or_doc_id,
            jurisdiction=jurisdiction,
            regulation=regulation,
            article=article,
            published_date=published_date,
            effective_date=effective_date,
            version_hash=version_hash,
            ingestion_timestamp=datetime.now(timezone.utc).isoformat(),
            title=title,
            text=text,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
