"""EUR-Lex fetcher – downloads regulation HTML/PDF from EUR-Lex."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from lios.config import settings
from lios.utils.logger import get_logger

logger = get_logger(__name__)

# Known CELEX identifiers for major sustainability regulations
KNOWN_REGULATIONS: dict[str, str] = {
    "CSRD":        "32022L2464",   # Corporate Sustainability Reporting Directive
    "SFDR":        "32019R2088",   # Sustainable Finance Disclosure Regulation
    "EU_TAXONOMY": "32020R0852",   # Taxonomy Regulation
    "CSDDD":       "32024L1760",   # Corporate Sustainability Due Diligence Directive
    "CBAM":        "32023R0956",   # Carbon Border Adjustment Mechanism
}


class EurLexFetcher:
    """Fetches regulation texts from EUR-Lex by CELEX number or direct URL."""

    BASE = settings.eurlex_base_url
    SEARCH_URL = "{base}/search.html?text={query}&scope=EURLEX&type=quick&lang=en"
    DOC_URL = "{base}/legal-content/EN/TXT/HTML/?uri=CELEX:{celex}"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Accept-Language": "en"},
            follow_redirects=True,
        )

    async def __aenter__(self) -> "EurLexFetcher":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def fetch_by_celex(self, celex: str) -> Optional[str]:
        """Return the full HTML text of a regulation by CELEX number."""
        url = self.DOC_URL.format(base=self.BASE, celex=celex)
        logger.info("Fetching EUR-Lex document: %s", url)
        response = await self._client.get(url)
        response.raise_for_status()
        return self._extract_text(response.text)

    async def fetch_known(self, short_name: str) -> Optional[str]:
        """Fetch a well-known regulation by its short name (e.g. 'CSRD')."""
        celex = KNOWN_REGULATIONS.get(short_name.upper())
        if celex is None:
            logger.warning("Unknown regulation short name: %s", short_name)
            return None
        return await self.fetch_by_celex(celex)

    async def download_to_disk(
        self, celex: str, dest_dir: Optional[Path] = None
    ) -> Path:
        """Download regulation text and save to *dest_dir*."""
        dest_dir = dest_dir or settings.regulations_path
        dest_dir.mkdir(parents=True, exist_ok=True)
        text = await self.fetch_by_celex(celex)
        if text is None:
            raise ValueError(f"No content for CELEX {celex}")
        dest = dest_dir / f"{celex}.txt"
        dest.write_text(text, encoding="utf-8")
        logger.info("Saved %s (%d chars) → %s", celex, len(text), dest)
        return dest

    # ── Private ───────────────────────────────────────────────────────────────
    @staticmethod
    def _extract_text(html: str) -> str:
        """Strip boilerplate; keep article text and headings."""
        soup = BeautifulSoup(html, "lxml")
        # Remove scripts, styles, nav
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        # EUR-Lex article bodies are usually in <div class="eli-main-title"> and <p>
        paragraphs = soup.find_all(["p", "h1", "h2", "h3", "article"])
        lines = [p.get_text(separator=" ", strip=True) for p in paragraphs]
        return "\n".join(line for line in lines if line)
