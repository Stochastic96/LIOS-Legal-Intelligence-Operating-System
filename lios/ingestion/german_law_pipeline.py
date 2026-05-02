"""German federal law ingester for LIOS.

Downloads XML ZIPs from gesetze-im-internet.de (no auth, no WAF), parses
per-paragraph text, and appends new chunks to ``data/corpus/legal_chunks.jsonl``
before ingesting them into ChromaDB.

Usage::

    from lios.ingestion.german_law_pipeline import ingest_german_laws
    added = ingest_german_laws()

CLI::

    python scripts/ingest_german_law.py
    python scripts/ingest_german_law.py --laws bgb lksg --dry-run
"""

from __future__ import annotations

import io
import json
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError as _import_err:  # pragma: no cover
    raise ImportError(
        "httpx is required for German law ingestion. "
        "Install with: pip install httpx"
    ) from _import_err

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CORPUS = Path("data/corpus/legal_chunks.jsonl")
_ZIP_URL = "https://www.gesetze-im-internet.de/{abbr}/xml.zip"

GERMAN_LAWS: dict[str, dict[str, str]] = {
    "bgb": {"name": "BGB", "full": "Bürgerliches Gesetzbuch"},
    "lksg": {"name": "LkSG", "full": "Lieferkettensorgfaltspflichtengesetz"},
    "behg": {"name": "BEHG", "full": "Brennstoffemissionshandelsgesetz"},
    "ksg": {"name": "ksg", "full": "Klimaschutzgesetz"},
    "uwg": {"name": "UWG", "full": "Gesetz gegen den unlauteren Wettbewerb"},
    "gmbhg": {"name": "GmbHG", "full": "GmbH-Gesetz"},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_german_laws(
    laws: list[str] | None = None,
    corpus_path: str | Path = _DEFAULT_CORPUS,
    dry_run: bool = False,
) -> int:
    """Download, parse, and append German federal law chunks.

    Args:
        laws:        Abbreviation keys to fetch (default: all in GERMAN_LAWS).
        corpus_path: Destination JSONL file.
        dry_run:     If *True*, print what would be written but make no changes.

    Returns:
        Number of new chunks added (0 in dry-run mode).
    """
    if laws is None:
        laws = list(GERMAN_LAWS.keys())

    corpus_path = Path(corpus_path)
    existing_prefixes = _load_existing_prefixes(corpus_path)
    new_chunks: list[dict[str, Any]] = []

    print(f"Fetching German laws: {', '.join(l.upper() for l in laws)}")

    for abbr in laws:
        if abbr not in GERMAN_LAWS:
            print(f"  WARNING: unknown law abbreviation {abbr!r}, skipping")
            continue
        chunks = fetch_law(abbr)
        novel = [c for c in chunks if c["text"][:80] not in existing_prefixes]
        print(f"  {abbr.upper()} → {len(novel)} paragraphs extracted")
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


def fetch_law(abbr: str) -> list[dict[str, Any]]:
    """Download and parse a single German law by abbreviation.

    Args:
        abbr: Key from GERMAN_LAWS (e.g. ``"bgb"``).

    Returns:
        List of chunk dicts.  Empty list if download or parse fails.
    """
    meta = GERMAN_LAWS.get(abbr)
    if meta is None:
        raise ValueError(
            f"Unknown law abbreviation: {abbr!r}. Must be one of {list(GERMAN_LAWS)}"
        )

    url = _ZIP_URL.format(abbr=abbr)
    logger.info("Downloading %s from %s", meta["name"], url)

    try:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            zip_bytes = resp.content
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.error("Failed to download %s: %s", url, exc)
        return []

    return parse_law_zip(zip_bytes, meta["name"])


def parse_law_zip(zip_bytes: bytes, regulation: str) -> list[dict[str, Any]]:
    """Parse a ZIP archive containing an XML law document.

    Args:
        zip_bytes:  Raw bytes of the downloaded ZIP file.
        regulation: Canonical regulation name (e.g. ``"BGB"``).

    Returns:
        List of chunk dicts extracted from the XML.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            xml_names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
            if not xml_names:
                logger.warning("No XML file found in ZIP for %s", regulation)
                return []
            # Pick the largest XML file (the main law document)
            xml_name = max(xml_names, key=lambda n: zf.getinfo(n).file_size)
            xml_bytes = zf.read(xml_name)
    except (zipfile.BadZipFile, KeyError) as exc:
        logger.error("Failed to read ZIP for %s: %s", regulation, exc)
        return []

    return parse_law_xml(xml_bytes, regulation)


def parse_law_xml(xml_bytes: bytes, regulation: str) -> list[dict[str, Any]]:
    """Parse the XML bytes of a German law document.

    The gesetze-im-internet.de XML structure::

        <dokument>
          <norm>
            <metadaten>
              <enbez>§ 1</enbez>
              <titel format="parat">Rechtsfähigkeit des Menschen</titel>
            </metadaten>
            <textdaten>
              <text format="XML">
                <Content>
                  <P>Die Rechtsfähigkeit ...</P>
                </Content>
              </text>
            </textdaten>
          </norm>
          ...
        </dokument>

    Args:
        xml_bytes:  Raw XML bytes.
        regulation: Canonical regulation name for chunk metadata.

    Returns:
        List of chunk dicts.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.error("XML parse error for %s: %s", regulation, exc)
        return []

    chunks: list[dict[str, Any]] = []
    for norm in root.iter("norm"):
        meta = norm.find("metadaten")
        if meta is None:
            continue

        enbez_el = meta.find("enbez")
        titel_el = meta.find("titel")

        enbez = (enbez_el.text or "").strip() if enbez_el is not None else ""
        titel = (titel_el.text or "").strip() if titel_el is not None else ""

        # Skip norms without a paragraph/article identifier
        if not enbez:
            continue

        text = _extract_norm_text(norm)
        if len(text) < 20:
            continue

        article = enbez
        title_part = f" {titel}" if titel else ""
        full_text = f"{article}{title_part}\n{text}".strip()

        chunks.append({
            "text": full_text,
            "regulation": regulation,
            "article": article,
            "celex_id": "",
            "source": "gesetze-im-internet.de",
            "jurisdiction": "DE",
            "chunk_type": "paragraph",
        })

    return chunks


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_norm_text(norm: ET.Element) -> str:
    """Extract all paragraph text from a <norm> element."""
    parts: list[str] = []
    textdaten = norm.find("textdaten")
    if textdaten is None:
        return ""
    # Walk all descendants; collect <P> element text regardless of namespace
    for elem in textdaten.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "P":
            text = "".join(elem.itertext()).strip()
            if text:
                parts.append(text)
    return " ".join(parts)


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
