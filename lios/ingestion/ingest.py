"""Ingest legal documents into FAISS + pickle for fast retrieval.

Pipeline
--------
1. Load documents from a JSON file (list of ``{title, text, source, language}``).
2. Clean each text (strip HTML, normalise whitespace).
3. Chunk each document into overlapping windows (400 words, 50-word overlap).
4. Embed all chunks with sentence-transformers (all-MiniLM-L6-v2).
5. Build a FAISS IndexFlatIP and persist it.
6. Save the chunk metadata list to a pickle file.

Usage::

    python -m lios.ingestion.ingest
    # or
    from lios.ingestion.ingest import run_ingestion
    run_ingestion("data/raw/legal_dataset.json")
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any

from lios.ingestion.cleaner import clean_text
from lios.retrieval.embedder import embed_texts
from lios.retrieval.vector_store import build_flat_index, save_index

logger = logging.getLogger(__name__)

_DEFAULT_INPUT = Path("data/raw/legal_dataset.json")
_DEFAULT_INDEX = Path("data/index.faiss")
_DEFAULT_CHUNKS = Path("data/chunks.pkl")

CHUNK_SIZE = 400     # words per chunk
CHUNK_OVERLAP = 50   # overlapping words between consecutive chunks


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _chunk_words(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split *text* into overlapping word windows.

    Args:
        text:    Plain text to chunk.
        size:    Window size in words.
        overlap: Number of words shared between consecutive windows.

    Returns:
        List of chunk strings.
    """
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunk_words = words[start : start + size]
        chunks.append(" ".join(chunk_words))
        if start + size >= len(words):
            break
        start += step
    return chunks


# ---------------------------------------------------------------------------
# Main ingestion function
# ---------------------------------------------------------------------------


def run_ingestion(
    input_path: str | Path = _DEFAULT_INPUT,
    index_path: str | Path = _DEFAULT_INDEX,
    chunks_path: str | Path = _DEFAULT_CHUNKS,
) -> int:
    """Load, clean, chunk, embed, and index legal documents.

    Args:
        input_path:  Path to the JSON file with legal documents.
        index_path:  Destination path for the FAISS index.
        chunks_path: Destination path for the pickled chunks list.

    Returns:
        Total number of chunks ingested.
    """
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
        word_chunks = _chunk_words(cleaned)

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
        logger.warning("No chunks produced – check input file.")
        return 0

    logger.info("Generated %d chunks; computing embeddings…", len(all_chunks))
    vectors = embed_texts(all_texts)

    logger.info("Building FAISS index…")
    index = build_flat_index(vectors)

    save_index(index, index_path)
    logger.info("FAISS index saved to %s", index_path)

    chunks_file = Path(chunks_path)
    chunks_file.parent.mkdir(parents=True, exist_ok=True)
    with chunks_file.open("wb") as fh:
        pickle.dump(all_chunks, fh)
    logger.info("Chunks saved to %s (%d entries)", chunks_file, len(all_chunks))

    return len(all_chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    total = run_ingestion()
    print(f"Ingested {total} chunks.")
