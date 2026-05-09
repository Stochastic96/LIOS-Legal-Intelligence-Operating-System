#!/usr/bin/env python3
"""Batch PDF importer — moves desktop PDFs into data/pdfs/, ingests with lawyer-lens
annotation, and seeds the content stack.

Usage
-----
python scripts/ingest_desktop_pdfs.py              # full run
python scripts/ingest_desktop_pdfs.py --dry-run    # show what would be indexed, no writes
python scripts/ingest_desktop_pdfs.py --lens-only  # re-annotate existing corpus (no new PDFs)
python scripts/ingest_desktop_pdfs.py --stack-only # rebuild content stack from existing corpus
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

_DESKTOP = Path.home() / "Desktop"
_PDF_DIR = Path("data/pdfs")
_CORPUS  = Path("data/corpus/legal_chunks.jsonl")

# ---------------------------------------------------------------------------
# Regulation name inference map (filename stem fragments → canonical name)
# ---------------------------------------------------------------------------

_REGULATION_MAP: dict[str, str] = {
    "csrd":             "CSRD",
    "esrs":             "ESRS",
    "taxonomy":         "EU_TAXONOMY",
    "sfdr":             "SFDR",
    "gdpr":             "GDPR",
    "dsgvo":            "GDPR",
    "lksg":             "LkSG",
    "cs3d":             "CS3D",
    "csddd":            "CS3D",
    "eudr":             "EUDR",
    "cbam":             "CBAM",
    "nis2":             "NIS2",
    "dora":             "DORA",
    "ai_act":           "AI_ACT",
    "ai-act":           "AI_ACT",
    "mifid":            "MiFID2",
    "srd2":             "SRD2",
    "whistleblower":    "WHISTLEBLOWER",
    "green_deal":       "GREEN_DEAL",
    "green-deal":       "GREEN_DEAL",
    "green_claims":     "GREEN_CLAIMS",
    "greenwashing":     "GREENWASHING",
    "paris":            "PARIS_AGREEMENT",
    "mica":             "MiCA",
    "data_act":         "DATA_ACT",
    "reach":            "REACH",
    "ied":              "IED",
    "ets":              "ETS",
    "batteries":        "EU_BATTERIES",
    "hgb":              "HGB",
    "aktg":             "AktG",
    "gmbhg":            "GmbHG",
    "bgb":              "BGB",
    "behg":             "BEHG",
    "ksg":              "KSG",
    "uwg":              "UWG",
    "wphg":             "WpHG",
    "zpo":              "ZPO",
    "bdsg":             "BDSG",
    "prodhaftg":        "ProdHaftG",
    "egaktg":           "EGAktG",
    "teu":              "TEU",
    "tfeu":             "TFEU",
    "aeuv":             "TFEU",
    "charter":          "EU_CHARTER",
    "van_gend":         "CJEU_VAN_GEND",
    "van-gend":         "CJEU_VAN_GEND",
    "costa":            "CJEU_COSTA",
    "cassis":           "CJEU_CASSIS",
    "francovich":       "CJEU_FRANCOVICH",
    "rancovich":        "CJEU_FRANCOVICH",   # typo in filename
    "schrems":          "CJEU_SCHREMS",
    "google_spain":     "CJEU_GOOGLE_SPAIN",
    "google-spain":     "CJEU_GOOGLE_SPAIN",
    "janecek":          "CJEU_JANECEK",
    "tcfd":             "TCFD",
    "ifrs_s1":          "IFRS_S1",
    "ifrs_s2":          "IFRS_S2",
    "ifrs-s1":          "IFRS_S1",
    "ifrs-s2":          "IFRS_S2",
    "gri":              "GRI",
    "efrag":            "EFRAG",
    "vsme":             "VSME",
    "oecd":             "OECD_DD",
    "ungp":             "UNGP",
    "un_guiding":       "UNGP",
    "omnibus":          "CSRD_OMNIBUS",
    "horizontal":       "EU_COMPETITION",
    "merger":           "EU_COMPETITION",
    "ec_merger":        "EU_COMPETITION",
    "englisch_ksg":     "KSG",
    "fit_for_55":       "FIT_FOR_55",
    "fit-for-55":       "FIT_FOR_55",
    "annual_report":    "GRI",
    "gri-policy":       "GRI",
    "finance-events":   "EFRAG",
    "policymakers":     "GRI",
}


def _infer_regulation(stem: str) -> str:
    stem_lower = stem.lower().replace(" ", "_")
    for key, name in _REGULATION_MAP.items():
        if key in stem_lower:
            return name
    return stem.upper()[:30]


# ---------------------------------------------------------------------------
# Step 1: Copy desktop PDFs to data/pdfs/
# ---------------------------------------------------------------------------

def copy_desktop_pdfs(dry_run: bool = False) -> list[Path]:
    """Copy all PDFs from Desktop to data/pdfs/. Returns list of destination paths."""
    _PDF_DIR.mkdir(parents=True, exist_ok=True)
    desktop_pdfs = sorted(_DESKTOP.glob("*.pdf"))
    copied: list[Path] = []

    print(f"\nStep 1: Copying {len(desktop_pdfs)} PDFs from Desktop → data/pdfs/")
    for src in desktop_pdfs:
        dst = _PDF_DIR / src.name
        if dst.exists():
            copied.append(dst)
            continue
        if dry_run:
            print(f"  [dry-run] would copy: {src.name}")
        else:
            shutil.copy2(src, dst)
        copied.append(dst)

    already = sum(1 for p in copied if (_PDF_DIR / p.name).exists())
    print(f"  {len(desktop_pdfs)} PDFs total, {already} already in data/pdfs/")
    return copied


# ---------------------------------------------------------------------------
# Step 2: Ingest PDFs with lawyer-lens annotation
# ---------------------------------------------------------------------------

def ingest_pdfs_with_lens(pdf_files: list[Path], dry_run: bool = False) -> int:
    """Extract chunks from each PDF, annotate with lawyer-lens, append to corpus."""
    try:
        import pypdf
    except ImportError:
        print("ERROR: pypdf not installed. Run: pip install 'pypdf>=4.0.0'")
        return 0

    from lios.ingestion.pdf_ingester import extract_chunks_from_pdf, _load_existing_prefixes
    from lios.ingestion.lawyer_lens import annotate_chunk

    existing_prefixes = _load_existing_prefixes(_CORPUS)
    total_new = 0

    print(f"\nStep 2: Ingesting {len(pdf_files)} PDFs with lawyer-lens annotation")

    for i, pdf_path in enumerate(pdf_files, 1):
        t0 = time.time()
        regulation = _infer_regulation(pdf_path.stem)
        try:
            chunks = extract_chunks_from_pdf(pdf_path)
        except Exception as exc:
            print(f"  [{i:02d}/{len(pdf_files)}] {pdf_path.name} → ERROR: {exc}")
            continue

        # Filter to novel chunks
        novel = [c for c in chunks if c.get("text", "")[:80] not in existing_prefixes]

        if not novel:
            print(f"  [{i:02d}/{len(pdf_files)}] {pdf_path.name} → already indexed ({len(chunks)} chunks)")
            continue

        # Annotate with lawyer lenses
        for chunk in novel:
            chunk["regulation"] = chunk.get("regulation") or regulation
            annotate_chunk(chunk)
            existing_prefixes.add(chunk.get("text", "")[:80])

        elapsed = time.time() - t0
        print(f"  [{i:02d}/{len(pdf_files)}] {pdf_path.name} → {len(novel)} chunks [{elapsed:.1f}s]")

        if not dry_run:
            _CORPUS.parent.mkdir(parents=True, exist_ok=True)
            with _CORPUS.open("a", encoding="utf-8") as fh:
                for chunk in novel:
                    fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        total_new += len(novel)

    return total_new


# ---------------------------------------------------------------------------
# Step 3: Rebuild content stack from corpus
# ---------------------------------------------------------------------------

def rebuild_content_stack(dry_run: bool = False) -> int:
    from lios.intelligence.content_stack_builder import build_stack_from_corpus
    print("\nStep 3: Building content stack from corpus")
    n = build_stack_from_corpus(save=not dry_run)
    print(f"  Generated {n} content stack entries")
    if dry_run:
        print("  [dry-run] stack not saved")
    return n


# ---------------------------------------------------------------------------
# Step 4: Refresh retriever
# ---------------------------------------------------------------------------

def refresh_retriever() -> None:
    print("\nStep 4: Refreshing HybridRetriever index")
    try:
        import lios.retrieval.hybrid_retriever as _hr
        with _hr._retriever_lock:
            _hr._retriever_singleton = _hr.HybridRetriever()
        print("  HybridRetriever refreshed ✓")
    except Exception as exc:
        print(f"  WARNING: could not refresh retriever: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest desktop PDFs into LIOS corpus")
    parser.add_argument("--dry-run",    action="store_true", help="Show what would happen, no writes")
    parser.add_argument("--lens-only",  action="store_true", help="Re-annotate existing corpus, skip copy+ingest")
    parser.add_argument("--stack-only", action="store_true", help="Rebuild content stack only, skip everything else")
    args = parser.parse_args()

    t_start = time.time()

    if args.stack_only:
        rebuild_content_stack(dry_run=args.dry_run)
    elif args.lens_only:
        rebuild_content_stack(dry_run=args.dry_run)
    else:
        pdfs = copy_desktop_pdfs(dry_run=args.dry_run)
        total_chunks = ingest_pdfs_with_lens(pdfs, dry_run=args.dry_run)
        stack_entries = rebuild_content_stack(dry_run=args.dry_run)

        if not args.dry_run and total_chunks > 0:
            refresh_retriever()

        elapsed = time.time() - t_start
        print(f"\n{'='*60}")
        print(f"  PDFs processed  : {len(pdfs)}")
        print(f"  New chunks      : {total_chunks}")
        print(f"  Stack entries   : {stack_entries}")
        print(f"  Total time      : {elapsed:.1f}s")
        if args.dry_run:
            print("  Mode            : DRY RUN — no files written")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
