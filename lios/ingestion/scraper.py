"""Scraper for German federal law at https://www.gesetze-im-internet.de."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.gesetze-im-internet.de"
_TOC_URL = f"{_BASE_URL}/Teilliste_GESAMT.xml"


def scrape_law(abbr: str) -> list[dict[str, Any]]:
    """Scrape all articles of a single German statute from gesetze-im-internet.de.

    Fetches ``/<abbr>/index.html``, parses each ``§`` section, and returns the
    extracted articles.

    Args:
        abbr: The official abbreviation used in the URL path, e.g. ``"bgb"``
              or ``"tmg"``.

    Returns:
        A list of dicts, each with keys:
        - ``title`` (str)  – section heading
        - ``text``  (str)  – section body text (German)
        - ``source`` (str) – canonical URL of the section
        - ``language`` (str) – always ``"de"``

    Example::

        articles = scrape_law("bgb")
        for a in articles[:3]:
            print(a["title"], "|", a["source"])
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError(
            "httpx and beautifulsoup4 are required for scraping. "
            "Install them with: pip install httpx beautifulsoup4"
        ) from exc

    index_url = f"{_BASE_URL}/{abbr.lower()}/index.html"
    logger.info("Fetching index: %s", index_url)

    try:
        resp = httpx.get(index_url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Failed to fetch law index for %r: %s", abbr, exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # The table of contents lists links to individual section pages.
    section_links: list[str] = []
    for a_tag in soup.select("a[href]"):
        href: str = a_tag["href"]
        # Section pages follow the pattern __<number>.html
        if href.startswith("__") and href.endswith(".html"):
            section_links.append(f"{_BASE_URL}/{abbr.lower()}/{href}")

    if not section_links:
        # Fallback: attempt to parse sections directly from the index page
        logger.warning("No section links found in index for %r; parsing inline.", abbr)
        return _parse_inline(abbr, soup, index_url)

    articles: list[dict[str, Any]] = []
    for url in section_links:
        article = _fetch_section(url)
        if article:
            articles.append(article)

    logger.info("Scraped %d sections for law %r.", len(articles), abbr)
    return articles


def _fetch_section(url: str) -> dict[str, Any] | None:
    """Fetch and parse a single section page."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    try:
        resp = httpx.get(url, timeout=20, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Skipping section %s: %s", url, exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.find("h2") or soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    content_div = soup.find("div", {"class": "jnhtml"}) or soup.find("article")
    if content_div:
        text = content_div.get_text(separator=" ", strip=True)
    else:
        text = soup.get_text(separator=" ", strip=True)

    return {
        "title": title,
        "text": text,
        "source": url,
        "language": "de",
    }


def _parse_inline(
    abbr: str, soup: Any, base_url: str
) -> list[dict[str, Any]]:
    """Fallback: parse law sections directly from the index page."""
    articles: list[dict[str, Any]] = []
    for section in soup.find_all(["div", "section"], class_=True):
        heading = section.find(["h2", "h3", "h4"])
        if not heading:
            continue
        title = heading.get_text(strip=True)
        text = section.get_text(separator=" ", strip=True)
        if len(text) < 50:
            continue
        articles.append(
            {
                "title": title,
                "text": text,
                "source": base_url,
                "language": "de",
            }
        )
    return articles
