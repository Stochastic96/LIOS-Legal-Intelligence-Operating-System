"""EUR-Lex regulatory document fetcher.

Fetches full regulation text for the four core EU sustainability regulations
using their CELEX IDs via the EUR-Lex public HTML endpoint and parses
per-article text with BeautifulSoup.

No authentication is required — all documents are publicly accessible.
"""

from __future__ import annotations

import logging
import re
from typing import Any

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError as _import_err:  # pragma: no cover
    raise ImportError(
        "httpx and beautifulsoup4 are required for EUR-Lex ingestion. "
        "Install with: pip install httpx beautifulsoup4"
    ) from _import_err

logger = logging.getLogger(__name__)

# Maps the CLI short key to regulation metadata.
REGULATIONS: dict[str, dict[str, str]] = {
    "csrd": {
        "celex_id": "32022L2464",
        "regulation": "CSRD",
        "published_date": "2022-12-16",
        "effective_date": "2023-01-05",
    },
    "esrs": {
        "celex_id": "32023R2772",
        "regulation": "ESRS",
        "published_date": "2023-12-22",
        "effective_date": "2024-01-01",
    },
    "taxonomy": {
        "celex_id": "32020R0852",
        "regulation": "EU_TAXONOMY",
        "published_date": "2020-06-22",
        "effective_date": "2020-07-12",
    },
    "sfdr": {
        "celex_id": "32019R2088",
        "regulation": "SFDR",
        "published_date": "2019-12-09",
        "effective_date": "2021-03-10",
    },
}

_HTML_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{celex_id}"

# Safety cap on sibling elements scanned when searching for an article's end
# in the generic fallback parser.  Prevents runaway traversal on malformed HTML.
_MAX_SIBLING_SCAN_DEPTH: int = 60
_ARTICLE_RE = re.compile(r"Article\s+(\d+[a-z]?)", re.IGNORECASE)


def fetch_regulation(reg_key: str) -> list[dict[str, Any]]:
    """Fetch a regulation by its short key and return a list of article dicts.

    Args:
        reg_key: One of ``"csrd"``, ``"esrs"``, ``"taxonomy"``, ``"sfdr"``.

    Returns:
        A list of dicts, each with keys:
        ``article``, ``title``, ``text``, ``celex_id``, ``regulation``,
        ``published_date``, ``effective_date``.

    Raises:
        ValueError: If *reg_key* is not recognised.
    """
    if reg_key not in REGULATIONS:
        raise ValueError(
            f"Unknown regulation key: {reg_key!r}. Must be one of {list(REGULATIONS)}"
        )

    meta = REGULATIONS[reg_key]
    celex_id = meta["celex_id"]
    url = _HTML_URL.format(celex_id=celex_id)
    logger.info("Fetching %s from %s", reg_key.upper(), url)

    try:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(url, headers={"Accept-Language": "en"})
            resp.raise_for_status()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = _parse_articles(soup, meta)
    logger.info("Extracted %d articles for %s", len(articles), reg_key.upper())
    return articles


def fetch_regulation_from_html(html: str, reg_key: str) -> list[dict[str, Any]]:
    """Parse articles from pre-fetched HTML.  Used in tests.

    Args:
        html:    Raw EUR-Lex HTML string.
        reg_key: One of ``"csrd"``, ``"esrs"``, ``"taxonomy"``, ``"sfdr"``.
    """
    if reg_key not in REGULATIONS:
        raise ValueError(f"Unknown regulation key: {reg_key!r}")

    meta = REGULATIONS[reg_key]
    soup = BeautifulSoup(html, "html.parser")
    return _parse_articles(soup, meta)


# ---------------------------------------------------------------------------
# Internal HTML parsing helpers
# ---------------------------------------------------------------------------


def _parse_articles(soup: Any, meta: dict[str, str]) -> list[dict[str, Any]]:
    """Dispatch to the most appropriate parsing strategy."""
    celex_id = meta["celex_id"]
    regulation = meta["regulation"]

    # Strategy 1: structured eli-subdivision divs (modern EUR-Lex format)
    articles = _parse_eli_subdivisions(soup, celex_id, regulation, meta)
    if articles:
        return articles

    # Strategy 2: ti-art paragraph markers (older EUR-Lex format)
    articles = _parse_ti_art_markers(soup, celex_id, regulation, meta)
    if articles:
        return articles

    # Strategy 3: generic heading scan
    return _parse_generic(soup, celex_id, regulation, meta)


def _parse_eli_subdivisions(
    soup: Any, celex_id: str, regulation: str, meta: dict[str, str]
) -> list[dict[str, Any]]:
    """Parse articles from ``<div class="eli-subdivision" id="art_N">`` elements."""
    articles = []
    for div in soup.find_all("div", class_="eli-subdivision"):
        art_id: str = div.get("id", "")
        article_num = _article_num_from_id(art_id)
        if article_num is None:
            continue

        title, text = _extract_title_and_text(div, article_num)
        if not text:
            continue

        articles.append(
            _make_article_dict(article_num, title, text, celex_id, regulation, meta)
        )

    return articles


def _parse_ti_art_markers(
    soup: Any, celex_id: str, regulation: str, meta: dict[str, str]
) -> list[dict[str, Any]]:
    """Parse articles by locating ``<p class="ti-art">Article N</p>`` markers."""
    # Collect all ti-art tags (or paragraphs that look like article headings)
    ti_tags = soup.find_all(class_="ti-art")
    if not ti_tags:
        ti_tags = [
            p
            for p in soup.find_all("p")
            if _ARTICLE_RE.match(p.get_text(strip=True))
            and len(p.get_text(strip=True)) < 60
        ]
    if not ti_tags:
        return []

    articles = []
    for tag in ti_tags:
        m = _ARTICLE_RE.search(tag.get_text(strip=True))
        if not m:
            continue
        article_num = m.group(1)

        # Optional subtitle immediately following
        title = f"Article {article_num}"
        next_sib = tag.find_next_sibling()
        if next_sib and _has_class(next_sib, "sti-art"):
            title = next_sib.get_text(strip=True)

        # Collect paragraph text until the next ti-art marker
        text_parts: list[str] = []
        current = tag.find_next_sibling()
        while current is not None:
            if _has_class(current, "ti-art"):
                break
            if _ARTICLE_RE.match(current.get_text(strip=True)[:60]):
                break
            part = current.get_text(separator=" ", strip=True)
            if part:
                text_parts.append(part)
            current = current.find_next_sibling()

        text = _clean_text(" ".join(text_parts))
        if len(text) < 30:
            continue

        articles.append(
            _make_article_dict(article_num, title, text, celex_id, regulation, meta)
        )

    return articles


def _parse_generic(
    soup: Any, celex_id: str, regulation: str, meta: dict[str, str]
) -> list[dict[str, Any]]:
    """Generic fallback: scan all elements for 'Article N' headings."""
    articles = []
    seen: set[str] = set()

    for elem in soup.find_all(["h1", "h2", "h3", "h4", "p"]):
        raw = elem.get_text(strip=True)
        m = _ARTICLE_RE.match(raw)
        if not m or len(raw) > 80:
            continue
        article_num = m.group(1)
        if article_num in seen:
            continue
        seen.add(article_num)

        # Gather text from siblings until the next article heading
        text_parts: list[str] = []
        current = elem.find_next_sibling()
        steps = 0
        while current is not None and steps < _MAX_SIBLING_SCAN_DEPTH:
            if _ARTICLE_RE.match(current.get_text(strip=True)[:60]):
                break
            part = current.get_text(separator=" ", strip=True)
            if part:
                text_parts.append(part)
            current = current.find_next_sibling()
            steps += 1

        text = _clean_text(" ".join(text_parts))
        if len(text) < 30:
            continue

        articles.append(
            _make_article_dict(
                article_num, f"Article {article_num}", text, celex_id, regulation, meta
            )
        )

    return articles


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _extract_title_and_text(div: Any, article_num: str) -> tuple[str, str]:
    """Return (title, body_text) from an eli-subdivision div."""
    # Prefer the subtitle (sti-art) as the human-readable title;
    # fall back to stripping the article number from the ti-art heading.
    sti_tag = div.find(class_="sti-art")
    ti_tag = div.find(class_="ti-art")
    if sti_tag:
        title = sti_tag.get_text(strip=True)
    elif ti_tag:
        raw_title = ti_tag.get_text(strip=True)
        title = re.sub(r"^Article\s+\d+[a-z]?\s*", "", raw_title, flags=re.IGNORECASE).strip()
        title = title or f"Article {article_num}"
    else:
        title = f"Article {article_num}"

    # Collect body paragraphs
    text_parts: list[str] = []
    for elem in div.find_all(["p", "td"]):
        cls = elem.get("class") or []
        if isinstance(cls, str):
            cls = [cls]
        # Skip the article title/subtitle itself
        if any(c in ("ti-art", "sti-art") for c in cls):
            continue
        part = elem.get_text(separator=" ", strip=True)
        if part:
            text_parts.append(part)

    if not text_parts:
        # Fallback: take all text, stripping the heading
        for heading in div.find_all(class_=["ti-art", "sti-art"]):
            heading.decompose()
        raw = div.get_text(separator=" ", strip=True)
        text_parts = [raw]

    return title, _clean_text(" ".join(text_parts))


def _article_num_from_id(elem_id: str) -> str | None:
    """Extract article number from id like ``art_1``, ``art_2a``, ``art_10``."""
    if not elem_id:
        return None
    m = re.search(r"\bart[_-](\d+[a-z]?)\b", elem_id, re.IGNORECASE)
    return m.group(1) if m else None


def _has_class(tag: Any, cls: str) -> bool:
    tag_cls = tag.get("class") or []
    if isinstance(tag_cls, str):
        tag_cls = [tag_cls]
    return cls in tag_cls


def _clean_text(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


def _make_article_dict(
    article_num: str,
    title: str,
    text: str,
    celex_id: str,
    regulation: str,
    meta: dict[str, str],
) -> dict[str, Any]:
    return {
        "article": f"Art.{article_num}",
        "title": title,
        "text": text,
        "celex_id": celex_id,
        "regulation": regulation,
        "published_date": meta["published_date"],
        "effective_date": meta["effective_date"],
    }
