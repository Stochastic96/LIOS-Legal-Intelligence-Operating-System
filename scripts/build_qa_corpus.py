#!/usr/bin/env python3
"""
Build Q&A enriched corpus for LIOS.

Reads every chunk in data/corpus/legal_chunks.jsonl, generates multiple
question-answer pairs per chunk using template patterns, then appends them
as new searchable documents to the corpus and rebuilds the FAISS index.

This makes LIOS answer faster and more accurately because common legal
questions now have pre-computed, authoritative answers in the retrieval index.

Usage:
  python3 scripts/build_qa_corpus.py             # full run
  python3 scripts/build_qa_corpus.py --limit 500 # test on 500 chunks
  python3 scripts/build_qa_corpus.py --no-embed  # skip rebuilding FAISS
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

REPO_ROOT   = pathlib.Path(__file__).parent.parent
CORPUS_FILE = REPO_ROOT / "data/corpus/legal_chunks.jsonl"
QA_FILE     = REPO_ROOT / "data/corpus/qa_pairs.jsonl"

# ── Q&A template patterns ──────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Light cleanup: collapse excessive whitespace only."""
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _generate_qa_pairs(chunk: dict) -> list[dict]:
    """Generate Q&A pairs from a single corpus chunk."""
    reg      = chunk.get("regulation", "EU law")
    article  = chunk.get("article", "")
    title    = chunk.get("title", "")
    text     = _clean(chunk.get("text", ""))
    juris    = chunk.get("jurisdiction", "EU")

    if len(text) < 40:
        return []

    # Short descriptive title for the article
    art_ref = f"{reg} {article}".strip() if article else reg
    doc_ref = title if title else art_ref

    pairs: list[tuple[str, str]] = []

    # Pattern 1 — "What does X say?" → full text
    pairs.append((
        f"What does {art_ref} say?",
        text,
    ))

    # Pattern 2 — "What are the requirements under X?" (if text has "shall" or "must")
    if re.search(r'\b(shall|must|required|obligation)\b', text, re.I):
        pairs.append((
            f"What are the requirements under {art_ref}?",
            text,
        ))

    # Pattern 3 — definition questions (if text starts with a definition)
    m = re.match(r"['‘’]?([A-Z][a-z][\w\s]{3,30})['’]?\s+means\s+", text)
    if m:
        term = m.group(1).strip()
        pairs.append((
            f"What is the definition of '{term}' under {reg}?",
            text,
        ))

    # Pattern 4 — threshold / number questions
    if re.search(r'\b(\d[\d,\.]+)\s*(employees?|million|EUR|percent|%|tonnes?|MW|GWh)\b', text, re.I):
        pairs.append((
            f"What are the thresholds or numerical limits in {art_ref}?",
            text,
        ))

    # Pattern 5 — scope / applicability
    if re.search(r'\b(applies? to|in scope|undertakings?|companies|entities)\b', text, re.I):
        pairs.append((
            f"Who does {art_ref} apply to?",
            text,
        ))

    # Pattern 6 — deadline / timeline
    if re.search(r'\b(by|until|from|deadline|date|year|202[0-9]|203[0-9])\b', text, re.I):
        pairs.append((
            f"What are the deadlines or timelines under {art_ref}?",
            text,
        ))

    # Pattern 7 — penalty / sanction
    if re.search(r'\b(penalt|sanction|fine|infring|breach|violat)\b', text, re.I):
        pairs.append((
            f"What are the penalties or sanctions under {art_ref}?",
            text,
        ))

    # Build output dicts
    now = datetime.now(timezone.utc).isoformat()
    results = []
    for q, a in pairs:
        qa_text = f"Q: {q}\nA: {a}"
        uid = hashlib.md5(qa_text.encode()).hexdigest()[:16]
        results.append({
            "chunk_id":           f"qa-{uid}",
            "source_url":         chunk.get("source_url", ""),
            "celex_or_doc_id":    chunk.get("celex_or_doc_id", ""),
            "jurisdiction":       juris,
            "regulation":         reg,
            "article":            article,
            "published_date":     chunk.get("published_date", ""),
            "effective_date":     chunk.get("effective_date", ""),
            "version_hash":       uid,
            "ingestion_timestamp": now,
            "title":              doc_ref,
            "text":               qa_text,
            "qa_pair":            True,
            "question":           q,
            "source_chunk_id":    chunk.get("chunk_id", ""),
        })
    return results


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",    type=int, default=0,    help="Process only first N chunks (0=all)")
    parser.add_argument("--no-embed", action="store_true",     help="Skip rebuilding FAISS/embeddings")
    parser.add_argument("--append",   action="store_true",     help="Append to existing qa_pairs.jsonl instead of overwriting")
    args = parser.parse_args()

    if not CORPUS_FILE.exists():
        sys.exit(f"Corpus not found: {CORPUS_FILE}")

    print(f"\nLIOS Q&A Corpus Builder")
    print(f"  Source: {CORPUS_FILE}")
    print(f"  Output: {QA_FILE}")

    # Count total chunks
    total = sum(1 for _ in CORPUS_FILE.open())
    limit = args.limit or total
    print(f"  Processing {limit:,} of {total:,} chunks\n")

    # Generate Q&A pairs
    t0 = time.time()
    written = 0
    skipped = 0
    by_pattern: dict[str, int] = {}

    mode = "a" if args.append else "w"
    with CORPUS_FILE.open() as src, QA_FILE.open(mode, encoding="utf-8") as dst:
        for i, line in enumerate(src):
            if i >= limit:
                break
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            pairs = _generate_qa_pairs(chunk)
            for p in pairs:
                dst.write(json.dumps(p, ensure_ascii=False) + "\n")
                # Track pattern stats from question
                q = p["question"]
                if "definition" in q.lower():
                    by_pattern["definition"] = by_pattern.get("definition", 0) + 1
                elif "requirements" in q.lower():
                    by_pattern["requirements"] = by_pattern.get("requirements", 0) + 1
                elif "thresholds" in q.lower():
                    by_pattern["thresholds"] = by_pattern.get("thresholds", 0) + 1
                elif "apply to" in q.lower():
                    by_pattern["applicability"] = by_pattern.get("applicability", 0) + 1
                elif "deadlines" in q.lower():
                    by_pattern["deadlines"] = by_pattern.get("deadlines", 0) + 1
                elif "penalties" in q.lower():
                    by_pattern["penalties"] = by_pattern.get("penalties", 0) + 1
                else:
                    by_pattern["general"] = by_pattern.get("general", 0) + 1
                written += 1

            if (i + 1) % 2000 == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                eta = (limit - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1:>6}/{limit:>6}]  Q&A pairs so far: {written:>7,}  ETA: {eta/60:.1f}min")

    elapsed = time.time() - t0
    qa_per_chunk = written / limit if limit else 0
    print(f"\n{'='*60}")
    print(f"  Generated {written:,} Q&A pairs from {limit:,} chunks")
    print(f"  Avg {qa_per_chunk:.1f} pairs per chunk  |  Took {elapsed:.1f}s")
    print(f"\n  Breakdown by pattern type:")
    for pattern, count in sorted(by_pattern.items(), key=lambda x: -x[1]):
        print(f"    {pattern:<16}: {count:>8,}")
    print(f"{'='*60}\n")

    if args.no_embed:
        print("Skipping embedding rebuild (--no-embed). Run scripts/build_corpus.py to rebuild.")
        return

    # Merge qa_pairs.jsonl into legal_chunks.jsonl and rebuild index
    print("Merging Q&A pairs into corpus and rebuilding index...")
    _rebuild_corpus_with_qa()


def _rebuild_corpus_with_qa():
    """Append Q&A pairs to corpus and rebuild FAISS index."""
    import subprocess, os

    # First: merge qa_pairs into a combined corpus
    combined_file = REPO_ROOT / "data/corpus/legal_chunks_with_qa.jsonl"
    existing_ids: set[str] = set()

    with CORPUS_FILE.open() as f:
        existing_chunk_ids = set()
        for line in f:
            try:
                c = json.loads(line)
                existing_chunk_ids.add(c.get("chunk_id", ""))
            except Exception:
                pass

    # Read new QA pairs, deduplicate
    new_qa = []
    if QA_FILE.exists():
        with QA_FILE.open() as f:
            for line in f:
                try:
                    c = json.loads(line)
                    if c.get("chunk_id", "") not in existing_chunk_ids:
                        new_qa.append(c)
                except Exception:
                    pass

    print(f"  Adding {len(new_qa):,} new Q&A chunks to corpus...")

    # Append to legal_chunks.jsonl
    with CORPUS_FILE.open("a", encoding="utf-8") as f:
        for c in new_qa:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    total_now = sum(1 for _ in CORPUS_FILE.open())
    print(f"  Corpus now: {total_now:,} chunks")

    # Rebuild embeddings
    print("  Rebuilding FAISS index (this may take a few minutes)...")
    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/build_corpus.py"), "--embed-only"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=False,
    )
    if result.returncode != 0:
        print("  WARNING: Embedding rebuild failed. Run: python3 scripts/build_corpus.py --embed-only")
    else:
        print("  Index rebuilt successfully.")


if __name__ == "__main__":
    main()
