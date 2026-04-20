"""Ingest raw legal documents into the LIOS JSONL corpus.

Accepts a list of document dicts (or a path to a JSON file containing them)
and appends provenance-aware chunks to ``data/corpus/legal_chunks.jsonl``.

Document dict format::

    {
        "title":       "Breach of Contract",          # required
        "text":        "A breach of contract ...",     # required
        "source":      "BGB §280",                     # optional – used as article id
        "regulation":  "BGB",                          # optional
        "source_url":  "https://example.com",          # optional
        "jurisdiction": "DE",                          # optional (default "EU")
        "published_date": "2002-01-01",               # optional
    }

Usage from the command line::

    python -m lios.ingestion.ingest path/to/documents.json

Usage from Python::

    from lios.ingestion.ingest import ingest_documents
    ingest_documents([{"title": "...", "text": "...", "source": "BGB §1"}])
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from lios.ingestion.models import LegalChunk

_DEFAULT_OUTPUT = Path("data/corpus/legal_chunks.jsonl")


def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
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
        if chunk:
            chunks.append(chunk)
    return chunks


def ingest_documents(
    docs: list[dict[str, Any]],
    output_path: str | Path = _DEFAULT_OUTPUT,
    chunk_size: int = 400,
    overlap: int = 50,
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
            text: str = doc.get("text", "")
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m lios.ingestion.ingest <documents.json> [output.jsonl]")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else _DEFAULT_OUTPUT

    with input_file.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if isinstance(data, dict):
        # Support a single document dict
        data = [data]

    count = ingest_documents(data, output_path=output_file)
    print(f"Ingested {count} chunks into {output_file}")
