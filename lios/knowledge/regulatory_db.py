"""Regulatory database – loads and indexes all regulations."""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any

from lios.knowledge.regulations import csrd, esrs, eu_taxonomy, sfdr
from lios.logging_setup import get_logger

logger = get_logger(__name__)

# Maximum number of distinct query strings to cache per RegulatoryDatabase instance
_SEARCH_CACHE_MAXSIZE = 256


class RegulatoryDatabase:
    """Central registry of all supported regulations.

    Performance characteristics (after init):
    - ``search_articles`` is O(k) per query word where *k* is the number of
      articles that contain that word, versus the previous O(n·m) full scan.
    - Results for identical (query, regulation) pairs are memoised in an
      instance-level LRU cache bounded to ``_SEARCH_CACHE_MAXSIZE`` entries.
    """

    REGULATION_MODULES: dict[str, Any] = {
        "CSRD": csrd,
        "ESRS": esrs,
        "EU_TAXONOMY": eu_taxonomy,
        "SFDR": sfdr,
    }

    # Alias map so callers can use common names
    ALIASES: dict[str, str] = {
        "csrd": "CSRD",
        "esrs": "ESRS",
        "taxonomy": "EU_TAXONOMY",
        "eu taxonomy": "EU_TAXONOMY",
        "eu_taxonomy": "EU_TAXONOMY",
        "sfdr": "SFDR",
        "sustainable finance": "SFDR",
    }

    def __init__(self) -> None:
        self._regulations: dict[str, dict[str, Any]] = {}
        # Inverted index: word → list of (reg_key, article_dict) pairs
        self._keyword_index: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        # Flat article lookup: (reg_key, article_id) → enriched article dict
        self._article_cache: dict[tuple[str, str], dict[str, Any]] = {}
        # Instance-level LRU search result cache: OrderedDict used as an LRU
        self._search_cache: OrderedDict[tuple[str, str | None], tuple[tuple, ...]] = OrderedDict()
        self._load_all()
        self._build_indices()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        for key, module in self.REGULATION_MODULES.items():
            self._regulations[key] = {
                "name": getattr(module, "NAME", key),
                "full_name": getattr(module, "FULL_NAME", ""),
                "effective_date": getattr(module, "effective_date", ""),
                "last_updated": getattr(module, "last_updated", ""),
                "jurisdictions": getattr(module, "jurisdictions", ["EU"]),
                "articles": getattr(module, "articles", []),
                "module": module,
            }
        logger.debug("Loaded %d regulations.", len(self._regulations))

    def _build_indices(self) -> None:
        """Build inverted keyword index and flat article cache (O(n) once at startup)."""
        total_articles = 0
        for reg_key, reg in self._regulations.items():
            full_name = reg["full_name"]
            for article in reg["articles"]:
                art_id = article.get("id", "")
                enriched = {
                    "regulation": reg_key,
                    "regulation_full_name": full_name,
                    "article_id": art_id,
                    "title": article.get("title", ""),
                    "text": article.get("text", ""),
                    "topic": article.get("topic", ""),
                    # keywords field is optional; fall back to empty list
                    "keywords": article.get("keywords", []),
                }
                self._article_cache[(reg_key, art_id)] = enriched

                # Index every word in title + text + topic + explicit keywords
                searchable = (
                    enriched["title"]
                    + " "
                    + enriched["text"]
                    + " "
                    + enriched["topic"]
                    + " "
                    + " ".join(enriched["keywords"])
                ).lower()
                for word in re.findall(r"[a-z0-9]{3,}", searchable):
                    self._keyword_index.setdefault(word, []).append((reg_key, enriched))

                total_articles += 1

        logger.info(
            "Built inverted index: %d articles, %d unique index terms.",
            total_articles,
            len(self._keyword_index),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_regulation(self, name: str) -> dict[str, Any] | None:
        """Return regulation data by name or alias."""
        key = self._resolve_key(name)
        return self._regulations.get(key)

    def get_all_regulations(self) -> list[dict[str, Any]]:
        """Return metadata for all regulations (without full article text)."""
        result = []
        for key, reg in self._regulations.items():
            result.append(
                {
                    "key": key,
                    "name": reg["name"],
                    "full_name": reg["full_name"],
                    "effective_date": reg["effective_date"],
                    "last_updated": reg["last_updated"],
                    "jurisdictions": reg["jurisdictions"],
                    "article_count": len(reg["articles"]),
                }
            )
        return result

    def _cached_search(
        self,
        query: str,
        regulation: str | None,
    ) -> tuple[tuple, ...]:
        """Return a sorted tuple of ((reg_key, art_id), score) pairs.

        Results are stored in an instance-level OrderedDict LRU cache so that
        the cache is bound to this object's lifetime (no class-level shared
        state) and does not prevent garbage collection of the instance.
        """
        cache_key = (query, regulation)
        if cache_key in self._search_cache:
            # Move to end (most recently used)
            self._search_cache.move_to_end(cache_key)
            return self._search_cache[cache_key]

        # Compute result
        keywords = [w for w in re.findall(r"[a-z0-9]{3,}", query.lower())]
        result: tuple[tuple, ...]
        if not keywords:
            result = ()
        else:
            allowed_regs: set[str] | None = None
            if regulation:
                key = self._resolve_key(regulation)
                if key not in self._regulations:
                    result = ()
                    self._store_in_cache(cache_key, result)
                    return result
                allowed_regs = {key}

            # Aggregate scores using the inverted index (O(k) per keyword)
            scores: dict[tuple[str, str], int] = {}
            for kw in keywords:
                for reg_key, enriched in self._keyword_index.get(kw, []):
                    if allowed_regs and reg_key not in allowed_regs:
                        continue
                    cache_k = (reg_key, enriched["article_id"])
                    scores[cache_k] = scores.get(cache_k, 0) + 1

            # Sort by descending score, then deterministically by article id
            sorted_items = sorted(
                scores.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1])
            )
            result = tuple(sorted_items)

        self._store_in_cache(cache_key, result)
        return result

    def _store_in_cache(
        self,
        cache_key: tuple[str, str | None],
        result: tuple[tuple, ...],
    ) -> None:
        """Insert into the LRU cache, evicting the oldest entry if at capacity."""
        if len(self._search_cache) >= _SEARCH_CACHE_MAXSIZE:
            self._search_cache.popitem(last=False)
        self._search_cache[cache_key] = result

    def search_articles(
        self,
        query: str,
        regulation: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fast keyword search using the inverted index.

        Time complexity: O(k) per keyword where *k* is the number of articles
        containing that keyword (was O(n·m) before).  Identical queries are
        served from an instance-level LRU cache in O(1).

        Returns:
            List of article dicts sorted by relevance score (descending).
        """
        sorted_items = self._cached_search(query, regulation)
        results = []
        for (reg_key, art_id), score in sorted_items:
            enriched = self._article_cache.get((reg_key, art_id))
            if enriched is None:
                continue
            results.append({**enriched, "relevance_score": score})
        return results

    def invalidate_cache(self) -> None:
        """Clear the LRU search cache (call after hot-reloading regulations)."""
        self._search_cache.clear()
        logger.info("Search cache cleared.")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_key(self, name: str) -> str:
        """Resolve an alias or key to a canonical regulation key."""
        name_lower = name.lower().strip()
        if name in self._regulations:
            return name
        if name_lower in self.ALIASES:
            return self.ALIASES[name_lower]
        # Case-insensitive direct key match
        for key in self._regulations:
            if key.lower() == name_lower:
                return key
        return name  # Return as-is; caller handles missing key
