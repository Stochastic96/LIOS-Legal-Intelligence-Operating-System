"""PDF corpus builder for LIOS.

Processes regulation PDFs placed in ``data/pdfs/`` and appends extracted
article chunks to ``data/corpus/legal_chunks.jsonl``, then ingests them into
ChromaDB.

No web scraping is needed — users download PDFs manually from their browser.

Usage::

    from lios.ingestion.pdf_ingester import ingest_pdfs
    added = ingest_pdfs()

CLI::

    python scripts/ingest_pdfs.py
    python scripts/ingest_pdfs.py --folder data/pdfs/ --dry-run
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_PDF_FOLDER = Path("data/pdfs")
_DEFAULT_CORPUS = Path("data/corpus/legal_chunks.jsonl")

# Regex for article-level split: matches "Article 1", "Article 2a", "Art. 1"
_ARTICLE_RE = re.compile(r"Article\s+(\d+[a-z]?)[\s\n]", re.IGNORECASE)

_TOKENS_PER_CHUNK = 500
_TOKEN_OVERLAP = 50

# Filename stem → canonical regulation name
_REGULATION_MAP: dict[str, str] = {
    "csrd": "CSRD",
    "esrs": "ESRS",
    "taxonomy": "EU_TAXONOMY",
    "sfdr": "SFDR",
    "gdpr": "GDPR",
    "lksg": "LkSG",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_pdfs(
    folder: str | Path = _DEFAULT_PDF_FOLDER,
    corpus_path: str | Path = _DEFAULT_CORPUS,
    dry_run: bool = False,
) -> int:
    """Scan *folder* for PDF files, extract chunks, and write to corpus.

    Args:
        folder:      Directory containing ``.pdf`` files.
        corpus_path: Destination JSONL file for deduplicated chunks.
        dry_run:     If *True*, print what would be written but make no changes.

    Returns:
        Number of new chunks added (0 in dry-run mode).
    """
    folder = Path(folder)
    corpus_path = Path(corpus_path)

    if not folder.exists():
        logger.warning("PDF folder does not exist: %s", folder)
        print(f"  WARNING: folder {folder} does not exist")
        return 0

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"  No .pdf files found in {folder}")
        return 0

    print(f"Scanning {folder}...")

    existing_prefixes = _load_existing_prefixes(corpus_path)
    new_chunks: list[dict[str, Any]] = []

    for pdf_path in pdf_files:
        chunks = extract_chunks_from_pdf(pdf_path)
        novel = [c for c in chunks if c["text"][:80] not in existing_prefixes]
        print(f"  {pdf_path.name} → {len(novel)} articles extracted")
        for c in novel:
            existing_prefixes.add(c["text"][:80])
        new_chunks.extend(novel)

    total = len(new_chunks)
    print(f"Total: {total} new chunks added to corpus and ChromaDB")

    if dry_run or total == 0:
        return 0

    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    with corpus_path.open("a", encoding="utf-8") as fh:
        for chunk in new_chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # Ingest into ChromaDB
    try:
        from lios.retrieval.chroma_retriever import ingest_jsonl
        ingest_jsonl(str(corpus_path), collection_name="eu_law")
    except Exception as exc:  # pragma: no cover
        logger.warning("ChromaDB ingest skipped: %s", exc)

    return total


def extract_chunks_from_pdf(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Extract article-level chunks from a single PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of chunk dicts with keys ``text``, ``regulation``, ``article``,
        ``celex_id``, ``source``, ``filename``, ``jurisdiction``,
        ``chunk_type``.
    """
    try:
        import pypdf
    except ImportError as exc:
        raise ImportError(
            "pypdf is required for PDF ingestion. "
            "Install with: pip install 'pypdf>=4.0.0'"
        ) from exc

    pdf_path = Path(pdf_path)
    regulation = _infer_regulation(pdf_path.stem)

    # Extract full text page by page
    full_text = _extract_full_text(pypdf, pdf_path)
    if not full_text.strip():
        return []

    # Try article-level splitting first
    chunks = _split_by_articles(full_text, regulation, pdf_path.name)
    if chunks:
        return chunks

    # Fall back to token-count splitting
    return _split_by_tokens(full_text, regulation, pdf_path.name)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_full_text(pypdf_module: Any, pdf_path: Path) -> str:
    """Read all pages from a PDF and return concatenated text."""
    parts: list[str] = []
    try:
        reader = pypdf_module.PdfReader(str(pdf_path))
        for page in reader.pages:
            text = page.extract_text() or ""
            parts.append(text)
    except Exception as exc:
        logger.warning("Failed to read %s: %s", pdf_path, exc)
    return "\n".join(parts)


def _split_by_articles(
    full_text: str, regulation: str, filename: str
) -> list[dict[str, Any]]:
    """Split text on 'Article N' markers.  Returns empty list if none found."""
    matches = list(_ARTICLE_RE.finditer(full_text))
    if not matches:
        return []

    chunks: list[dict[str, Any]] = []
    for i, match in enumerate(matches):
        article_num = match.group(1)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        text = full_text[start:end].strip()
        if len(text) < 30:
            continue
        chunks.append(_make_chunk(text, regulation, f"Art.{article_num}", filename, "article"))

    return chunks


def _split_by_tokens(
    full_text: str, regulation: str, filename: str
) -> list[dict[str, Any]]:
    """Split text into fixed-size token windows."""
    words = full_text.split()
    chunks: list[dict[str, Any]] = []
    idx = 0
    chunk_num = 1
    while idx < len(words):
        window = words[idx: idx + _TOKENS_PER_CHUNK]
        text = " ".join(window).strip()
        if len(text) >= 30:
            chunks.append(
                _make_chunk(text, regulation, f"chunk-{chunk_num}", filename, "chunk")
            )
            chunk_num += 1
        idx += _TOKENS_PER_CHUNK - _TOKEN_OVERLAP
    return chunks


def _make_chunk(
    text: str,
    regulation: str,
    article: str,
    filename: str,
    chunk_type: str,
) -> dict[str, Any]:
    return {
        "text": text,
        "regulation": regulation,
        "article": article,
        "celex_id": "",
        "source": "pdf",
        "filename": filename,
        "jurisdiction": "EU",
        "chunk_type": chunk_type,
    }


def _infer_regulation(stem: str) -> str:
    """Map a PDF filename stem to a canonical regulation name."""
    stem_lower = stem.lower()
    for key, name in _REGULATION_MAP.items():
        if key in stem_lower:
            return name
    return stem  # use filename stem as-is


def _load_existing_prefixes(corpus_path: Path) -> set[str]:
    """Return set of first-80-char text prefixes already in the corpus."""
    prefixes: set[str] = set()
    if not corpus_path.exists():
        return prefixes
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            text = obj.get("text", "")
            if text:
                prefixes.add(text[:80])
        except (json.JSONDecodeError, KeyError):
            continue
    return prefixes
