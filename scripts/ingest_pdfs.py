#!/usr/bin/env python3
"""CLI runner: ingest PDF files into the LIOS corpus.

Downloads and processes regulation PDFs placed in ``data/pdfs/`` (no web
scraping — users download files manually).

Usage::

    python scripts/ingest_pdfs.py
    python scripts/ingest_pdfs.py --folder data/pdfs/ --dry-run
    python scripts/ingest_pdfs.py --folder /path/to/pdfs --output /tmp/corpus.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lios.ingestion.pdf_ingester import ingest_pdfs  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan a folder of regulation PDFs, extract article chunks, and "
            "append new entries to data/corpus/legal_chunks.jsonl."
        )
    )
    parser.add_argument(
        "--folder",
        default=str(_ROOT / "data" / "pdfs"),
        metavar="PATH",
        help="Folder containing .pdf files. Default: data/pdfs/",
    )
    parser.add_argument(
        "--output",
        default=str(_ROOT / "data" / "corpus" / "legal_chunks.jsonl"),
        metavar="PATH",
        help="Output JSONL file. Default: data/corpus/legal_chunks.jsonl",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without modifying any files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    ingest_pdfs(
        folder=args.folder,
        corpus_path=args.output,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
