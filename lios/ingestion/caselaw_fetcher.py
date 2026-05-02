"""Case law fetcher for CJEU (EUR-Lex) and ECHR (HUDOC).

Fetches judgments relevant to GDPR, sustainability, and corporate law and
converts them to article dicts compatible with :func:`~lios.ingestion.legal_chunker.chunk_articles`.
"""

from __future__ import annotations

import logging
import re
from typing import Any

try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError as _err:
    raise ImportError(
        "httpx and beautifulsoup4 are required. "
        "Install with: pip install httpx beautifulsoup4"
    ) from _err

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CJEU — curated sustainability/GDPR-relevant Court of Justice cases
# ---------------------------------------------------------------------------

CJEU_CASES: list[dict[str, str]] = [
    {
        "celex_id": "62018CJ0311",
        "case_num": "C-311/18",
        "title": "Schrems II — GDPR international data transfers",
        "regulation": "GDPR",
        "published_date": "2020-07-16",
        "effective_date": "2020-07-16",
    },
    {
        "celex_id": "62014CJ0362",
        "case_num": "C-362/14",
        "title": "Schrems I — Safe Harbour invalid",
        "regulation": "GDPR",
        "published_date": "2015-10-06",
        "effective_date": "2015-10-06",
    },
    {
        "celex_id": "62012CJ0131",
        "case_num": "C-131/12",
        "title": "Google Spain — Right to be forgotten",
        "regulation": "GDPR",
        "published_date": "2014-05-13",
        "effective_date": "2014-05-13",
    },
    {
        "celex_id": "62018CJ0673",
        "case_num": "C-673/18",
        "title": "Planet49 — Cookie consent under GDPR",
        "regulation": "GDPR",
        "published_date": "2019-10-01",
        "effective_date": "2019-10-01",
    },
    {
        "celex_id": "62011CJ0258",
        "case_num": "C-258/11",
        "title": "Sweetman — Habitats Directive appropriate assessment",
        "regulation": "EU_TAXONOMY",
        "published_date": "2013-04-11",
        "effective_date": "2013-04-11",
    },
    {
        "celex_id": "62017CJ0441",
        "case_num": "C-441/17",
        "title": "Commission v Poland — Białowieża Forest logging",
        "regulation": "EU_TAXONOMY",
        "published_date": "2018-11-05",
        "effective_date": "2018-11-05",
    },
    {
        "celex_id": "62019CJ0272",
        "case_num": "C-272/19",
        "title": "VQ — Data processing by public bodies GDPR",
        "regulation": "GDPR",
        "published_date": "2020-06-09",
        "effective_date": "2020-06-09",
    },
    {
        "celex_id": "62020CJ0300",
        "case_num": "C-300/20",
        "title": "Unilever — Environmental product labelling CSRD",
        "regulation": "CSRD",
        "published_date": "2022-01-13",
        "effective_date": "2022-01-13",
    },
]

_EURLEX_HTML = (
    "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{celex_id}"
)

# ---------------------------------------------------------------------------
# ECHR — HUDOC search for privacy/environment-related cases
# ---------------------------------------------------------------------------

_HUDOC_SEARCH = (
    "https://hudoc.echr.coe.int/app/query/results"
    "?query=(contentsitename%3D%22ECHR%22+AND+"
    "(documentcollectionid2%3A%22GRANDCHAMBER%22+OR+documentcollectionid2%3A%22CHAMBER%22)"
    "+AND+{keyword})"
    "&select=itemid%2Cdocname%2Cjudgementdate%2Crespondent%2Ckeywords"
    "&sort=judgementdate+Descending&start=0&length={length}"
)
_HUDOC_DOC = (
    "https://hudoc.echr.coe.int/app/conversion/docx/html/body?library=ECHR&id={item_id}"
)

ECHR_TOPICS: list[dict[str, str]] = [
    {
        "keyword": "%22private+life%22+AND+%22personal+data%22",
        "regulation": "GDPR",
        "topic": "privacy_data",
    },
    {
        "keyword": "%22environment%22+AND+%22positive+obligations%22",
        "regulation": "CSRD",
        "topic": "environment",
    },
    {
        "keyword": "%22surveillance%22+AND+%22Article+8%22",
        "regulation": "GDPR",
        "topic": "surveillance",
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_cjeu_cases(
    case_list: list[dict[str, str]] | None = None,
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """Fetch CJEU judgment HTML from EUR-Lex and return article dicts.

    Args:
        case_list: Override the default :data:`CJEU_CASES` list.
        timeout: HTTP timeout in seconds.

    Returns:
        Article dicts compatible with :func:`~lios.ingestion.legal_chunker.chunk_articles`.
    """
    cases = case_list if case_list is not None else CJEU_CASES
    articles: list[dict[str, Any]] = []

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for case in cases:
            celex_id = case["celex_id"]
            url = _EURLEX_HTML.format(celex_id=celex_id)
            logger.info("Fetching CJEU %s from %s", case["case_num"], url)
            try:
                resp = client.get(url, headers={"Accept-Language": "en"})
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning("Skipping %s: %s", celex_id, exc)
                continue

            parsed = _parse_judgment_html(resp.text, case, source="cjeu")
            articles.extend(parsed)
            logger.info("Extracted %d sections from %s", len(parsed), case["case_num"])

    return articles


def fetch_echr_cases(
    topics: list[dict[str, str]] | None = None,
    max_per_topic: int = 5,
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """Query HUDOC for ECHR cases and fetch their text.

    Args:
        topics: List of topic dicts with ``keyword`` and ``regulation`` keys.
        max_per_topic: Max cases fetched per topic.
        timeout: HTTP timeout in seconds.

    Returns:
        Article dicts compatible with :func:`~lios.ingestion.legal_chunker.chunk_articles`.
    """
    topics = topics if topics is not None else ECHR_TOPICS
    articles: list[dict[str, Any]] = []

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for topic in topics:
            search_url = _HUDOC_SEARCH.format(
                keyword=topic["keyword"], length=max_per_topic
            )
            logger.info("Searching HUDOC topic: %s", topic["topic"])
            try:
                resp = client.get(search_url, headers={"Accept": "application/json"})
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("HUDOC search failed for %s: %s", topic["topic"], exc)
                continue

            for result in data.get("results", [])[:max_per_topic]:
                cols = result.get("columns", {})
                item_id = cols.get("itemid", "")
                doc_name = cols.get("docname", "Unknown")
                date_str = (cols.get("judgementdate") or "")[:10]
                if not item_id:
                    continue

                doc_url = _HUDOC_DOC.format(item_id=item_id)
                logger.info("Fetching ECHR %s (%s)", doc_name, item_id)
                try:
                    doc_resp = client.get(doc_url)
                    doc_resp.raise_for_status()
                except Exception as exc:
                    logger.warning("Failed to fetch ECHR %s: %s", item_id, exc)
                    continue

                case_meta = {
                    "celex_id": item_id,
                    "case_num": item_id,
                    "title": doc_name,
                    "regulation": topic["regulation"],
                    "published_date": date_str,
                    "effective_date": date_str,
                }
                parsed = _parse_judgment_html(doc_resp.text, case_meta, source="echr")
                articles.extend(parsed)

    return articles


def fetch_cjeu_cases_from_html(
    html: str, case_meta: dict[str, str]
) -> list[dict[str, Any]]:
    """Parse CJEU judgment from pre-fetched HTML. Used in tests."""
    return _parse_judgment_html(html, case_meta, source="cjeu")


def fetch_echr_cases_from_html(
    html: str, case_meta: dict[str, str]
) -> list[dict[str, Any]]:
    """Parse ECHR judgment from pre-fetched HTML. Used in tests."""
    return _parse_judgment_html(html, case_meta, source="echr")


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


def _parse_judgment_html(
    html: str, case_meta: dict[str, str], source: str = "cjeu"
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    articles = _parse_eli_sections(soup, case_meta, source)
    if articles:
        return articles

    articles = _parse_by_headings(soup, case_meta, source)
    if articles:
        return articles

    return _parse_paragraph_batches(soup, case_meta, source)


def _parse_eli_sections(
    soup: Any, meta: dict[str, str], source: str
) -> list[dict[str, Any]]:
    """Handle modern EUR-Lex structured judgments (eli-subdivision divs)."""
    sections: list[dict[str, Any]] = []
    for div in soup.find_all("div", class_="eli-subdivision"):
        title_tag = div.find(
            class_=re.compile(r"(ti-section|sti-section|ti-art|sti-art)")
        )
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            continue
        paras = [
            p.get_text(separator=" ", strip=True)
            for p in div.find_all("p")
            if not any(
                c in (p.get("class") or [])
                for c in ["ti-section", "sti-section", "ti-art", "sti-art"]
            )
        ]
        text = re.sub(r"\s+", " ", " ".join(paras)).strip()
        if len(text) < 50:
            continue
        sections.append(_make_article_dict(title, text, meta, source))
    return sections


def _parse_by_headings(
    soup: Any, meta: dict[str, str], source: str
) -> list[dict[str, Any]]:
    """One section per heading tag (h1-h3), collecting sibling paragraphs."""
    headings = soup.find_all(re.compile(r"^h[1-3]$"))
    if not headings:
        return []

    articles: list[dict[str, Any]] = []
    for heading in headings:
        title = heading.get_text(strip=True)
        if not title or len(title) > 200:
            continue
        parts: list[str] = []
        for sib in heading.next_siblings:
            name = getattr(sib, "name", None)
            if name and re.match(r"h[1-3]", name):
                break
            chunk = (
                sib.get_text(separator=" ", strip=True)
                if hasattr(sib, "get_text")
                else str(sib).strip()
            )
            if chunk:
                parts.append(chunk)
        text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if len(text) < 80:
            continue
        articles.append(_make_article_dict(title, text, meta, source))
    return articles


def _parse_paragraph_batches(
    soup: Any, meta: dict[str, str], source: str, batch: int = 15
) -> list[dict[str, Any]]:
    """Batch every `batch` substantive paragraphs into a section."""
    paras = [
        p.get_text(separator=" ", strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) >= 80
    ]
    if not paras:
        return []

    articles: list[dict[str, Any]] = []
    for i in range(0, len(paras), batch):
        text = " ".join(paras[i : i + batch])
        title = f"Section {i // batch + 1}"
        articles.append(_make_article_dict(title, text, meta, source))
    return articles


def _make_article_dict(
    title: str, text: str, meta: dict[str, str], source: str
) -> dict[str, Any]:
    celex_id = meta["celex_id"]
    source_url = (
        _EURLEX_HTML.format(celex_id=celex_id)
        if source == "cjeu"
        else _HUDOC_DOC.format(item_id=celex_id)
    )
    article_id = re.sub(r"\s+", "_", title[:60]).lower()
    return {
        "article": article_id,
        "title": title,
        "text": text,
        "celex_id": celex_id,
        "regulation": meta.get("regulation", "CJEU"),
        "published_date": meta.get("published_date", ""),
        "effective_date": meta.get("effective_date", ""),
        "source_url": source_url,
        "source": source,
        "case_num": meta.get("case_num", celex_id),
    }
