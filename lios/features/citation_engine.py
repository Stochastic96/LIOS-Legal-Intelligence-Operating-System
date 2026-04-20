"""Citation engine – scores and returns regulatory article citations."""

from __future__ import annotations

from dataclasses import dataclass

from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.retrieval.hybrid_retriever import HybridRetriever

# Base URLs for EU law
_BASE_URLS: dict[str, str] = {
    "CSRD": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2464",
    "ESRS": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R2772",
    "EU_TAXONOMY": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32020R0852",
    "SFDR": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32019R2088",
}


@dataclass
class Citation:
    regulation: str
    article_id: str
    title: str
    relevance_score: int
    url: str
    excerpt: str = ""


class CitationEngine:
    """Find and rank regulatory citations relevant to a query."""

    def __init__(
        self,
        db: RegulatoryDatabase | None = None,
        retriever: HybridRetriever | None = None,
    ) -> None:
        self.db = db or RegulatoryDatabase()
        # Reuse a shared HybridRetriever when provided to avoid duplicate model loads.
        self.retriever = retriever if retriever is not None else HybridRetriever()

    def get_citations(
        self,
        query: str,
        regulations: list[str] | None = None,
    ) -> list[Citation]:
        """Return top citations for the given query, optionally filtered by regulation."""
        # Prefer retrieval from provenance-aware corpus when available.
        retrieved = self.retriever.search(query=query, regulations=regulations, top_k=10)
        if retrieved:
            return [
                Citation(
                    regulation=r.chunk.get("regulation", "UNKNOWN"),
                    article_id=r.chunk.get("article", "unknown"),
                    title=r.chunk.get("title", ""),
                    relevance_score=max(1, int(round(r.total_score * 100))),
                    url=r.chunk.get("source_url", "https://eur-lex.europa.eu"),
                    excerpt=(r.chunk.get("text", "") or "")[:200],
                )
                for r in retrieved
            ]

        if regulations:
            all_results = []
            for reg in regulations:
                hits = self.db.search_articles(query, regulation=reg)
                all_results.extend(hits)
        else:
            all_results = self.db.search_articles(query)

        # Deduplicate
        seen: set[str] = set()
        citations: list[Citation] = []
        for hit in all_results:
            key = f"{hit['regulation']}:{hit['article_id']}"
            if key not in seen:
                seen.add(key)
                reg_key = hit["regulation"]
                url = _BASE_URLS.get(reg_key, "https://eur-lex.europa.eu")
                citations.append(
                    Citation(
                        regulation=reg_key,
                        article_id=hit["article_id"],
                        title=hit.get("title", ""),
                        relevance_score=hit["relevance_score"],
                        url=url,
                        excerpt=hit.get("text", "")[:200],
                    )
                )

        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        return citations[:10]
