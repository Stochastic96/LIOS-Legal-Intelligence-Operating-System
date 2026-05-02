#!/usr/bin/env python3
"""Build the EUR-Lex legal corpus from real EU regulatory documents.

Fetches HTML from EUR-Lex, extracts per-article text, splits into 400-600-token
chunks, and appends new entries to ``data/corpus/legal_chunks.jsonl``.
Existing entries (matched by celex_id + article) are skipped so the script is
safe to re-run.

Usage::

    python scripts/build_corpus.py --regulations csrd esrs taxonomy sfdr
    python scripts/build_corpus.py --regulations csrd
    python scripts/build_corpus.py --output /tmp/corpus.jsonl --regulations taxonomy
    python scripts/build_corpus.py --source pdf
    python scripts/build_corpus.py --source german --laws bgb lksg
    python scripts/build_corpus.py --extra-sources cjeu echr
    python scripts/build_corpus.py --extra-sources cjeu echr german
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the repository root is importable regardless of CWD.
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lios.ingestion.eurlex_fetcher import fetch_regulation  # noqa: E402
from lios.ingestion.legal_chunker import chunk_articles  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT = _ROOT / "data" / "corpus" / "legal_chunks.jsonl"
_ALL_REGULATIONS = ["csrd", "esrs", "taxonomy", "sfdr"]
_ALL_SOURCES = ["cjeu", "echr", "german"]


# ---------------------------------------------------------------------------
# Public helper — also importable by tests
# ---------------------------------------------------------------------------


def build_corpus(
    regulations: list[str],
    output_path: Path = _DEFAULT_OUTPUT,
    sources: list[str] | None = None,
) -> tuple[int, int]:
    """Fetch, chunk, and write regulations and case law to *output_path*.

    Args:
        regulations: Short keys such as ``["csrd", "esrs"]``.
        output_path: Destination JSONL file.
        sources: Optional list of additional sources: ``"cjeu"``, ``"echr"``, ``"german"``.

    Returns:
        ``(added, skipped)`` — counts of newly written and already-present chunks.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_existing_keys(output_path)
    new_chunk_dicts: list[dict] = []
    added = 0
    skipped = 0

    for reg_key in regulations:
        articles = fetch_regulation(reg_key)
        if not articles:
            print(f"  WARNING: no articles fetched for {reg_key.upper()}", file=sys.stderr)
            continue
        added, skipped = _ingest_articles(
            articles, existing, new_chunk_dicts, added, skipped
        )

    for source in sources or []:
        articles = _fetch_source(source)
        if not articles:
            print(f"  WARNING: no articles fetched for source={source}", file=sys.stderr)
            continue
        added, skipped = _ingest_articles(
            articles, existing, new_chunk_dicts, added, skipped
        )

    if new_chunk_dicts:
        with output_path.open("a", encoding="utf-8") as fh:
            for chunk_dict in new_chunk_dicts:
                fh.write(json.dumps(chunk_dict, ensure_ascii=False) + "\n")

    return added, skipped


def _fetch_source(source: str) -> list[dict]:
    """Dispatch to the appropriate fetcher for *source*."""
    if source == "cjeu":
        from lios.ingestion.caselaw_fetcher import fetch_cjeu_cases

        return fetch_cjeu_cases()
    if source == "echr":
        from lios.ingestion.caselaw_fetcher import fetch_echr_cases

        return fetch_echr_cases()
    if source == "german":
        from lios.ingestion.german_law_fetcher import fetch_german_laws

        return fetch_german_laws()
    raise ValueError(f"Unknown source: {source!r}. Must be one of {_ALL_SOURCES}")


def _ingest_articles(
    articles: list[dict],
    existing: set[str],
    new_chunk_dicts: list[dict],
    added: int,
    skipped: int,
) -> tuple[int, int]:
    chunks = chunk_articles(articles)
    for chunk in chunks:
        key = f"{chunk.celex_or_doc_id}|{chunk.article}"
        if key in existing:
            skipped += 1
        else:
            new_chunk_dicts.append(chunk.to_dict())
            existing.add(key)
            added += 1
    return added, skipped


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_existing_keys(path: Path) -> set[str]:
    """Return the set of ``celex_or_doc_id|article`` keys already in *path*."""
    keys: set[str] = set()
    if not path.exists():
        return keys
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                keys.add(f"{obj['celex_or_doc_id']}|{obj['article']}")
            except (json.JSONDecodeError, KeyError):
                continue
    return keys


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch EU regulations and case law and append new chunks to "
            "data/corpus/legal_chunks.jsonl."
        )
    )
    parser.add_argument(
        "--source",
        choices=["eurlex", "pdf", "german"],
        default="eurlex",
        metavar="SOURCE",
        help=(
            "Data source to ingest from. "
            "'eurlex' (default): fetch from EUR-Lex HTML. "
            "'pdf': process PDFs from data/pdfs/. "
            "'german': fetch German federal laws from gesetze-im-internet.de."
        ),
    )
    parser.add_argument(
        "--regulations",
        nargs="+",
        choices=_ALL_REGULATIONS,
        default=_ALL_REGULATIONS,
        metavar="REG",
        help=(
            f"Regulations to fetch (--source eurlex only). "
            f"One or more of: {', '.join(_ALL_REGULATIONS)}. "
            "Default: all four."
        ),
    )
    parser.add_argument(
        "--laws",
        nargs="+",
        default=None,
        metavar="LAW",
        help=(
            "German law abbreviations to fetch (--source german only). "
            "Default: all supported laws."
        ),
    )
    parser.add_argument(
        "--folder",
        default=str(_ROOT / "data" / "pdfs"),
        metavar="PATH",
        help="PDF folder (--source pdf only). Default: data/pdfs/",
    )
    parser.add_argument(
        "--extra-sources",
        nargs="+",
        choices=_ALL_SOURCES,
        default=[],
        dest="extra_sources",
        metavar="SRC",
        help=(
            f"Additional case-law / law sources. One or more of: {', '.join(_ALL_SOURCES)}. "
            "Default: none."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT),
        metavar="PATH",
        help=f"Output JSONL file path. Default: {_DEFAULT_OUTPUT}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    output_path = Path(args.output)

    if args.source == "pdf":
        from lios.ingestion.pdf_ingester import ingest_pdfs
        print(f"Source  : PDF files in {args.folder}")
        print(f"Output  : {output_path}")
        ingest_pdfs(folder=args.folder, corpus_path=output_path)
        return

    if args.source == "german":
        from lios.ingestion.german_law_pipeline import ingest_german_laws
        print(f"Source  : gesetze-im-internet.de")
        print(f"Output  : {output_path}")
        ingest_german_laws(laws=args.laws, corpus_path=output_path)
        return

    # Default: eurlex + optional extra sources (cjeu / echr / german via fetcher)
    regs = args.regulations
    srcs = args.extra_sources or []
    print(f"Regulations: {', '.join(r.upper() for r in regs) if regs else 'none'}")
    if srcs:
        print(f"Sources    : {', '.join(srcs)}")
    print(f"Output     : {output_path}")
    print(f"{added} chunks added, {skipped} skipped")


if __name__ == "__main__":
    main()
