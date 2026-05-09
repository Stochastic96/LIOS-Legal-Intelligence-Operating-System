"""Document indexer — extract, chunk, and append uploaded documents to the retrieval corpus.

Supports PDF (via pypdf), DOCX (via python-docx if available), and plain text.
After indexing, the HybridRetriever singleton is refreshed so new content is
immediately searchable without restarting the server.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from lios.logging_setup import get_logger

logger = get_logger(__name__)

_CORPUS_PATH = Path("data/corpus/legal_chunks.jsonl")
_CHUNK_SIZE_WORDS = 400
_CHUNK_OVERLAP_WORDS = 50


def _extract_text_pdf(content: bytes) -> str:
    """Extract text from a PDF byte buffer using pypdf."""
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p.strip() for p in pages if p.strip())
    except ImportError:
        raise ImportError("pypdf is required for PDF uploads. Install with: pip install pypdf")
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF: {exc}") from exc


def _extract_text_docx(content: bytes) -> str:
    """Extract text from a DOCX byte buffer using python-docx."""
    try:
        import io
        import docx  # type: ignore
        doc = docx.Document(io.BytesIO(content))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        raise ImportError("python-docx is required for DOCX uploads. Install with: pip install python-docx")
    except Exception as exc:
        raise ValueError(f"Failed to parse DOCX: {exc}") from exc


def _extract_text(content: bytes, filename: str, content_type: str) -> str:
    """Dispatch to the correct extractor based on file type."""
    fname_lower = filename.lower()
    if fname_lower.endswith(".pdf") or "pdf" in content_type:
        return _extract_text_pdf(content)
    if fname_lower.endswith(".docx") or "wordprocessingml" in content_type:
        return _extract_text_docx(content)
    # Fall back to plain text
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="replace")


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE_WORDS, overlap: int = _CHUNK_OVERLAP_WORDS) -> list[str]:
    """Split *text* into overlapping word-count chunks."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def _make_chunk_record(
    text: str,
    index: int,
    *,
    title: str,
    regulation: str,
    source_description: str,
    filename: str,
    doc_id: str,
) -> dict[str, Any]:
    """Build a legal_chunks.jsonl-compatible dict for one text chunk."""
    now = datetime.now(timezone.utc).isoformat()
    raw = f"{doc_id}|{index}|{text}".encode("utf-8")
    version_hash = sha256(raw).hexdigest()
    chunk_id = sha256(f"upload:{doc_id}:{index}".encode()).hexdigest()[:16]
    article_id = f"upload-{index + 1:03d}"

    return {
        "chunk_id": chunk_id,
        "source_url": "",
        "celex_or_doc_id": doc_id,
        "jurisdiction": "CUSTOM",
        "regulation": regulation,
        "article": article_id,
        "article_id": article_id,
        "published_date": now[:10],
        "effective_date": now[:10],
        "version_hash": version_hash,
        "ingestion_timestamp": now,
        "title": f"{title} — part {index + 1}",
        "text": text,
        "source": source_description or filename,
        "is_uploaded": True,
    }


def index_uploaded_document(
    content: bytes,
    filename: str,
    content_type: str,
    title: str,
    regulation: str,
    source_description: str,
) -> dict[str, Any]:
    """Extract, chunk, and append *content* to the retrieval corpus.

    Rebuilds the HybridRetriever's embedding index so uploaded content is
    immediately searchable without restarting the server.

    Returns:
        Dict with ``status``, ``chunks_added``, ``filename``.
    """
    text = _extract_text(content, filename, content_type)
    if not text.strip():
        return {"status": "error", "message": "No text could be extracted from the file.", "chunks_added": 0}

    doc_id = sha256(f"{filename}:{len(content)}".encode()).hexdigest()[:12]
    raw_chunks = _chunk_text(text)
    if not raw_chunks:
        return {"status": "error", "message": "Document is empty after chunking.", "chunks_added": 0}

    records = [
        _make_chunk_record(
            chunk, i,
            title=title,
            regulation=regulation,
            source_description=source_description,
            filename=filename,
            doc_id=doc_id,
        )
        for i, chunk in enumerate(raw_chunks)
    ]

    # Annotate each chunk with lawyer-lens metadata
    try:
        from lios.ingestion.lawyer_lens import annotate_chunk
        for record in records:
            annotate_chunk(record)
    except Exception as exc:
        logger.warning("Lawyer-lens annotation skipped: %s", exc)

    # Append to corpus JSONL
    _CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _CORPUS_PATH.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Indexed %d chunks from '%s' (regulation=%s)", len(records), filename, regulation)

    # Refresh the HybridRetriever singleton so new chunks are searchable.
    try:
        from lios.retrieval.hybrid_retriever import _retriever_singleton, _retriever_lock, HybridRetriever
        import lios.retrieval.hybrid_retriever as _hr_module
        with _retriever_lock:
            _hr_module._retriever_singleton = HybridRetriever()
        logger.info("HybridRetriever refreshed after upload.")
    except Exception as exc:
        logger.warning("Could not refresh retriever after upload: %s", exc)

    return {
        "status": "indexed",
        "filename": filename,
        "chunks_added": len(records),
        "regulation": regulation,
        "doc_id": doc_id,
    }
