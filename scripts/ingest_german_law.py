#!/usr/bin/env python3
"""CLI runner: ingest German federal laws into the LIOS corpus.

Downloads XML ZIPs from gesetze-im-internet.de (free public endpoint, no auth,
no WAF), parses per-paragraph text, and appends new chunks to the corpus.

Usage::

    python scripts/ingest_german_law.py
    python scripts/ingest_german_law.py --laws bgb lksg
    python scripts/ingest_german_law.py --laws bgb --dry-run
    python scripts/ingest_german_law.py --output /tmp/corpus.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lios.ingestion.german_law_pipeline import GERMAN_LAWS, ingest_german_laws  # noqa: E402

_ALL_LAWS = list(GERMAN_LAWS.keys())


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch German federal laws from gesetze-im-internet.de (XML ZIP) "
            "and append new chunks to data/corpus/legal_chunks.jsonl."
        )
    )
    parser.add_argument(
        "--laws",
        nargs="+",
        choices=_ALL_LAWS,
        default=_ALL_LAWS,
        metavar="LAW",
        help=(
            f"Law abbreviations to fetch. One or more of: {', '.join(_ALL_LAWS)}. "
            "Default: all."
        ),
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
        help="Show what would be downloaded and parsed without writing files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    ingest_german_laws(
        laws=args.laws,
        corpus_path=args.output,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
