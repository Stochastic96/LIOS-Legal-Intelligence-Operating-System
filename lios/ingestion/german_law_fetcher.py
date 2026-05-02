"""German national law fetcher using gesetze-im-internet.de XML ZIP downloads.

Fetches corporate, environmental and IT-security laws relevant to EU compliance
and converts them to article dicts compatible with
:func:`~lios.ingestion.legal_chunker.chunk_articles`.

No authentication required — all documents are publicly accessible.
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

try:
    import httpx
except ImportError as _err:
    raise ImportError(
        "httpx is required. Install with: pip install httpx"
    ) from _err

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Law registry — gesetze-im-internet.de abbreviations → metadata
# ---------------------------------------------------------------------------

GERMAN_LAWS: dict[str, dict[str, str]] = {
    "hgb": {
        "regulation": "HGB",
        "full_name": "Handelsgesetzbuch (German Commercial Code)",
        "jurisdiction": "Germany",
        "published_date": "1897-05-10",
        "effective_date": "1900-01-01",
    },
    "gmbhg": {
        "regulation": "GmbHG",
        "full_name": "GmbH-Gesetz (Limited Liability Company Act)",
        "jurisdiction": "Germany",
        "published_date": "1892-04-20",
        "effective_date": "1892-04-20",
    },
    "aktg": {
        "regulation": "AktG",
        "full_name": "Aktiengesetz (Stock Corporation Act)",
        "jurisdiction": "Germany",
        "published_date": "1965-09-06",
        "effective_date": "1966-01-01",
    },
    "krwg": {
        "regulation": "KrWG",
        "full_name": "Kreislaufwirtschaftsgesetz (Circular Economy Act)",
        "jurisdiction": "Germany",
        "published_date": "2012-02-24",
        "effective_date": "2012-06-01",
    },
    "bsig": {
        "regulation": "BSIG",
        "full_name": "BSI-Gesetz (IT Security Act)",
        "jurisdiction": "Germany",
        "published_date": "2009-08-14",
        "effective_date": "2009-08-14",
    },
    "umwg": {
        "regulation": "UmwG",
        "full_name": "Umwandlungsgesetz (Transformation Act)",
        "jurisdiction": "Germany",
        "published_date": "1994-10-28",
        "effective_date": "1995-01-01",
    },
}

_XML_ZIP_URL = "https://www.gesetze-im-internet.de/{abbrev}/xml.zip"
_SOURCE_URL = "https://www.gesetze-im-internet.de/{abbrev}/"

# XML namespace used inside norm text content
_XHTML_NS = "{http://www.w3.org/1999/xhtml}"

# Only ingest sections whose <enbez> matches a § or article number
_SECTION_RE = re.compile(r"^§\s*\d|^Art\.\s*\d|^Artikel\s*\d", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_german_laws(
    law_keys: list[str] | None = None,
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """Fetch German federal laws and return article dicts.

    Args:
        law_keys: Abbreviations to fetch (e.g. ``["hgb", "aktg"]``).
                  Defaults to all keys in :data:`GERMAN_LAWS`.
        timeout: HTTP timeout in seconds.

    Returns:
        Article dicts compatible with :func:`~lios.ingestion.legal_chunker.chunk_articles`.
    """
    keys = law_keys if law_keys is not None else list(GERMAN_LAWS)
    articles: list[dict[str, Any]] = []

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for abbrev in keys:
            meta = GERMAN_LAWS.get(abbrev)
            if meta is None:
                logger.warning("Unknown German law abbreviation: %r", abbrev)
                continue

            url = _XML_ZIP_URL.format(abbrev=abbrev)
            logger.info("Fetching %s from %s", meta["regulation"], url)
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning("Skipping %s: %s", abbrev, exc)
                continue

            parsed = parse_german_law_zip(resp.content, abbrev, meta)
            articles.extend(parsed)
            logger.info("Extracted %d sections from %s", len(parsed), meta["regulation"])

    return articles


def parse_german_law_zip(
    zip_bytes: bytes, abbrev: str, meta: dict[str, str]
) -> list[dict[str, Any]]:
    """Parse a gesetze-im-internet.de XML ZIP and return article dicts.

    Args:
        zip_bytes: Raw ZIP file content.
        abbrev: Law abbreviation (e.g. ``"hgb"``).
        meta: Entry from :data:`GERMAN_LAWS`.

    Returns:
        Article dicts compatible with :func:`~lios.ingestion.legal_chunker.chunk_articles`.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        logger.warning("Bad ZIP for %s: %s", abbrev, exc)
        return []

    with zf:
        xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
        if not xml_names:
            logger.warning("No XML files found in ZIP for %s", abbrev)
            return []

        articles: list[dict[str, Any]] = []
        for xml_name in sorted(xml_names):
            raw = zf.read(xml_name)
            articles.extend(_parse_xml(raw, abbrev, meta))

    return articles


def parse_german_law_xml(
    xml_bytes: bytes, abbrev: str, meta: dict[str, str]
) -> list[dict[str, Any]]:
    """Parse raw XML bytes from gesetze-im-internet.de. Used in tests."""
    return _parse_xml(xml_bytes, abbrev, meta)


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------


def _parse_xml(
    xml_bytes: bytes, abbrev: str, meta: dict[str, str]
) -> list[dict[str, Any]]:
    """Parse a <dokumente> XML file and extract one article per <norm>."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.warning("XML parse error for %s: %s", abbrev, exc)
        return []

    articles: list[dict[str, Any]] = []
    # Handle both <dokumente> root and direct <norm> sequences
    norms = root.iter("norm")

    for norm in norms:
        article = _parse_norm(norm, abbrev, meta)
        if article is not None:
            articles.append(article)

    return articles


def _parse_norm(
    norm: ET.Element, abbrev: str, meta: dict[str, str]
) -> dict[str, Any] | None:
    """Extract a single norm element into an article dict, or None if skippable."""
    metadaten = norm.find("metadaten")
    if metadaten is None:
        return None

    enbez = (metadaten.findtext("enbez") or "").strip()
    titel = (metadaten.findtext("titel") or "").strip()

    # Skip preamble, TOC entries, and non-section norms
    if not _SECTION_RE.match(enbez):
        return None

    text = _extract_norm_text(norm)
    if len(text) < 30:
        return None

    title = f"{enbez} {titel}".strip() if titel else enbez
    article_id = re.sub(r"[^\w]", "_", enbez).strip("_").lower()
    source_url = _SOURCE_URL.format(abbrev=abbrev)

    return {
        "article": article_id,
        "title": title,
        "text": text,
        "celex_id": f"{abbrev.upper()}:{enbez}",
        "regulation": meta["regulation"],
        "published_date": meta["published_date"],
        "effective_date": meta["effective_date"],
        "source_url": source_url,
        "jurisdiction": meta.get("jurisdiction", "Germany"),
    }


def _extract_norm_text(norm: ET.Element) -> str:
    """Extract all text content from <textdaten> → <text> elements."""
    textdaten = norm.find("textdaten")
    if textdaten is None:
        return ""

    text_elem = textdaten.find("text")
    if text_elem is None:
        return ""

    # Collect all text recursively from the content subtree
    parts: list[str] = []
    _collect_text(text_elem, parts)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _collect_text(elem: ET.Element, parts: list[str]) -> None:
    """Recursively collect text content, skipping XML tags but keeping text."""
    if elem.text and elem.text.strip():
        parts.append(elem.text.strip())
    for child in elem:
        _collect_text(child, parts)
        if child.tail and child.tail.strip():
            parts.append(child.tail.strip())
