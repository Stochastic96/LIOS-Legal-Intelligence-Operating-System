"""
Feature 3 – Citation Engine.

Formats legal citations into a consistent, audit-ready structure.
Citations link directly back to EUR-Lex article URLs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

from lios.config import settings

# CELEX → EUR-Lex HTML anchor pattern
_EURLEX_ARTICLE_URL = (
    "{base}/legal-content/EN/TXT/HTML/?uri=CELEX:{celex}#d1e{anchor}-1-1"
)

# Known CELEX numbers (extend as regulations are added)
_CELEX_MAP: dict[str, str] = {
    "CSRD":        "32022L2464",
    "SFDR":        "32019R2088",
    "EU_TAXONOMY": "32020R0852",
    "CSDDD":       "32024L1760",
    "CBAM":        "32023R0956",
    "ESRS":        "32023R2772",
}


@dataclass
class Citation:
    regulation: str          # short name, e.g. "CSRD"
    article: str             # e.g. "Art. 19a(1)"
    excerpt: str             # quoted text from the source
    source_url: Optional[str] = None
    celex: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "regulation": self.regulation,
            "article": self.article,
            "excerpt": self.excerpt,
            "source_url": self.source_url,
            "celex": self.celex,
        }


class CitationEngine:
    """
    Normalises raw citation dicts (from LLM output) into ``Citation`` objects
    and enriches them with EUR-Lex deep-link URLs.
    """

    def __init__(self, base_url: Optional[str] = None) -> None:
        self._base = (base_url or settings.eurlex_base_url).rstrip("/")

    def enrich(self, raw_citations: list[dict]) -> list[Citation]:
        """
        Convert raw LLM citation dicts to ``Citation`` objects with URLs.

        Expected dict keys: ``regulation``, ``article``, ``excerpt``.
        """
        enriched: list[Citation] = []
        for raw in raw_citations:
            reg = raw.get("regulation", "").strip()
            article = raw.get("article", "").strip()
            excerpt = raw.get("excerpt", "").strip()
            celex = _CELEX_MAP.get(reg.upper())

            url: Optional[str] = None
            if celex:
                url = f"{self._base}/legal-content/EN/TXT/HTML/?uri=CELEX:{celex}"

            enriched.append(
                Citation(
                    regulation=reg,
                    article=article,
                    excerpt=excerpt,
                    source_url=url,
                    celex=celex,
                )
            )
        return enriched

    @staticmethod
    def format_inline(citation: Citation) -> str:
        """Return a short inline citation string, e.g. '[CSRD Art. 19a(1)]'."""
        return f"[{citation.regulation} {citation.article}]"

    def format_bibliography(self, citations: list[Citation]) -> str:
        """Return a formatted bibliography block."""
        lines = []
        for i, c in enumerate(citations, start=1):
            line = f"{i}. {c.regulation} – {c.article}"
            if c.source_url:
                line += f" <{c.source_url}>"
            if c.excerpt:
                line += f'\n   "{c.excerpt}"'
            lines.append(line)
        return "\n".join(lines)
