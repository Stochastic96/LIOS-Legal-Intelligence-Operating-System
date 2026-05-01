"""Ingest raw legal documents into the LIOS corpus.

Two ingestion modes are provided:

1. **JSONL corpus** (primary, no extra deps):
   ``ingest_documents()`` appends provenance-aware chunks to
   ``data/corpus/legal_chunks.jsonl`` for use with
   :class:`~lios.retrieval.hybrid_retriever.HybridRetriever`.

2. **FAISS + pickle** (optional, requires ``lios[data]``):
   ``run_ingestion()`` embeds chunks with sentence-transformers and stores
   them in a FAISS index + pickle file for dense retrieval via
   :func:`~lios.retrieval.retriever.retrieve`.

Document dict format::

    {
        "title":          "Breach of Contract",   # required
        "text":           "A breach of ...",       # required
        "source":         "BGB 280",               # optional -- used as article id
        "regulation":     "BGB",                   # optional
        "source_url":     "https://example.com",   # optional
        "jurisdiction":   "DE",                    # optional (default "EU")
        "published_date": "2002-01-01",            # optional
    }

Usage from the command line::

    python -m lios.ingestion.ingest path/to/documents.json

Usage from Python::

    from lios.ingestion.ingest import ingest_documents
    ingest_documents([{"title": "...", "text": "...", "source": "BGB 1"}])
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from lios.ingestion.cleaner import clean_text
from lios.ingestion.models import LegalChunk

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT = Path("data/corpus/legal_chunks.jsonl")
_DEFAULT_INDEX = Path("data/index.faiss")
_DEFAULT_CHUNKS = Path("data/chunks.pkl")

CHUNK_SIZE = 400   # words per chunk
CHUNK_OVERLAP = 50  # overlapping words between consecutive chunks


# ---------------------------------------------------------------------------
# Shared chunking logic
# ---------------------------------------------------------------------------


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split *text* into overlapping word-based chunks.

    Args:
        text:       Raw text to split.
        chunk_size: Maximum number of words per chunk.
        overlap:    Number of words shared between consecutive chunks.

    Returns:
        List of text chunk strings.
    """
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        chunks.append(chunk)
    return chunks


# Keep the original name as an alias for callers that use _chunk_words.
# The wrapper maps the legacy ``size`` parameter name to ``chunk_size``.
def _chunk_words(
    text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Backwards-compatible alias for :func:`_chunk_text` with ``size`` parameter."""
    return _chunk_text(text, chunk_size=size, overlap=overlap)


# ---------------------------------------------------------------------------
# Mode 1 -- JSONL corpus pipeline (no extra dependencies)
# ---------------------------------------------------------------------------


def ingest_documents(
    docs: list[dict[str, Any]],
    output_path: str | Path = _DEFAULT_OUTPUT,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> int:
    """Ingest a list of document dicts, appending chunks to the JSONL corpus.

    Existing entries in the output file are preserved.  New chunks are appended
    so the file can be incrementally enriched.

    Args:
        docs:        List of document dicts (see module docstring for schema).
        output_path: Destination JSONL file.  Defaults to
                     ``data/corpus/legal_chunks.jsonl``.
        chunk_size:  Words per chunk (default 400).
        overlap:     Word overlap between consecutive chunks (default 50).

    Returns:
        Number of chunks written.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out.open("a", encoding="utf-8") as f:
        for doc in docs:
            title: str = doc.get("title", "Untitled")
            text: str = clean_text(doc.get("text", ""))
            regulation: str = doc.get("regulation", "CUSTOM")
            source: str = doc.get("source", "")
            source_url: str = doc.get("source_url", "")
            jurisdiction: str = doc.get("jurisdiction", "EU")
            published_date: str = doc.get("published_date", "")
            effective_date: str = doc.get("effective_date", published_date)

            if not text.strip():
                continue

            sub_chunks = _chunk_text(text, chunk_size=chunk_size, overlap=overlap)
            for idx, sub in enumerate(sub_chunks):
                article_id = source if source else f"chunk-{idx + 1}"
                if len(sub_chunks) > 1 and source:
                    article_id = f"{source}-part{idx + 1}"

                chunk = LegalChunk.create(
                    source_url=source_url,
                    celex_or_doc_id=source or regulation,
                    jurisdiction=jurisdiction,
                    regulation=regulation,
                    article=article_id,
                    published_date=published_date,
                    effective_date=effective_date,
                    title=title,
                    text=sub,
                )
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
                written += 1

    return written


# ---------------------------------------------------------------------------
# Mode 2 -- FAISS + pickle pipeline (requires lios[data])
# ---------------------------------------------------------------------------


def run_ingestion(
    input_path: str | Path = "data/raw/legal_dataset.json",
    index_path: str | Path = _DEFAULT_INDEX,
    chunks_path: str | Path = _DEFAULT_CHUNKS,
) -> int:
    """Load, clean, chunk, embed, and index legal documents into FAISS.

    Requires the ``lios[data]`` extras (``sentence-transformers``,
    ``faiss-cpu``).

    Args:
        input_path:  Path to the JSON file with legal documents.
        index_path:  Destination path for the FAISS index.
        chunks_path: Destination path for the pickled chunks list.

    Returns:
        Total number of chunks ingested.

    Raises:
        FileNotFoundError: If *input_path* does not exist.
        ImportError: If ``sentence-transformers`` or ``faiss-cpu`` are not
                     installed (install with ``pip install lios[data]``).
    """
    import pickle

    from lios.retrieval.embedder import embed_texts
    from lios.retrieval.vector_store import build_flat_index, save_index

    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with input_file.open("r", encoding="utf-8") as fh:
        documents: list[dict[str, Any]] = json.load(fh)

    logger.info("Loaded %d documents from %s", len(documents), input_file)

    all_chunks: list[dict[str, Any]] = []
    all_texts: list[str] = []

    for doc in documents:
        raw_text = doc.get("text", "")
        cleaned = clean_text(raw_text)
        word_chunks = _chunk_text(cleaned)

        for chunk_text in word_chunks:
            chunk_meta: dict[str, Any] = {
                "title": doc.get("title", ""),
                "text": chunk_text,
                "source": doc.get("source", ""),
                "language": doc.get("language", ""),
            }
            all_chunks.append(chunk_meta)
            all_texts.append(chunk_text)

    if not all_chunks:
        logger.warning("No chunks produced -- check input file.")
        return 0

    logger.info("Generated %d chunks; computing embeddings...", len(all_chunks))
    vectors = embed_texts(all_texts)

    logger.info("Building FAISS index...")
    index = build_flat_index(vectors)

    save_index(index, index_path)
    logger.info("FAISS index saved to %s", index_path)

    chunks_file = Path(chunks_path)
    chunks_file.parent.mkdir(parents=True, exist_ok=True)
    with chunks_file.open("wb") as fh:
        pickle.dump(all_chunks, fh)
    logger.info("Chunks saved to %s (%d entries)", chunks_file, len(all_chunks))

    return len(all_chunks)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python -m lios.ingestion.ingest <documents.json> [output.jsonl]")
        sys.exit(1)

    _input_file = Path(sys.argv[1])
    _output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else _DEFAULT_OUTPUT

    with _input_file.open("r", encoding="utf-8") as _fh:
        _data = json.load(_fh)

    if isinstance(_data, dict):
        _data = [_data]

    _count = ingest_documents(_data, output_path=_output_file)
    print(f"Ingested {_count} chunks into {_output_file}")
