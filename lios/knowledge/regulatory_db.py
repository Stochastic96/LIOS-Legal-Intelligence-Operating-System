"""Regulatory database – loads and indexes all regulations."""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from typing import Any

from lios.knowledge.regulations import csrd, esrs, eu_taxonomy, sfdr


class RegulatoryDatabase:
    """Central registry of all supported regulations."""

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
        # Inverted index: keyword -> list of (reg_key, article_index) tuples
        self._keyword_index: dict[str, list[tuple[str, int]]] = defaultdict(list)
        # LRU cache for repeated search queries (max 256 unique queries).
        # Uses OrderedDict so move_to_end() keeps the most-recently used entry last.
        self._search_cache: OrderedDict[
            tuple[str, str | None], list[dict[str, Any]]
        ] = OrderedDict()
        self._search_cache_max = 256
        self._load_all()
        self._build_index()

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

    def _build_index(self) -> None:
        """Build an inverted keyword index for O(k) keyword lookup.

        k = number of keywords in the search query.  The index maps each
        word to the (regulation_key, article_index) pairs that contain it,
        enabling sub-linear article retrieval compared to O(n) linear scan.
        """
        self._keyword_index.clear()
        for reg_key, reg in self._regulations.items():
            for idx, article in enumerate(reg["articles"]):
                combined = (
                    article.get("text", "") + " "
                    + article.get("title", "") + " "
                    + article.get("topic", "")
                ).lower()
                words = set(w for w in combined.split() if len(w) > 2)
                for word in words:
                    self._keyword_index[word].append((reg_key, idx))

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

    def search_articles(
        self,
        query: str,
        regulation: str | None = None,
    ) -> list[dict[str, Any]]:
        """Keyword search over article texts using an inverted index and query cache.

        Uses the pre-built inverted index for O(k) lookup (k = keyword count)
        rather than O(n) linear scan. Results for repeated identical queries
        are served from a bounded in-memory cache without re-computation.
        Returns list of matches sorted by relevance (number of keyword hits).
        """
        cache_key = (query.lower(), regulation)
        if cache_key in self._search_cache:
            # Move to end to mark as most-recently used
            self._search_cache.move_to_end(cache_key)
            return self._search_cache[cache_key]

        keywords = [w.lower() for w in query.split() if len(w) > 2]
        if not keywords:
            return []

        filter_key: str | None = None
        if regulation:
            resolved = self._resolve_key(regulation)
            if resolved in self._regulations:
                filter_key = resolved
            else:
                # Unknown regulation – return empty, consistent with original behaviour
                return []

        # Count keyword hits per (reg_key, article_index) via the inverted index
        hit_counts: dict[tuple[str, int], int] = defaultdict(int)
        for kw in keywords:
            for reg_key, art_idx in self._keyword_index.get(kw, []):
                if filter_key is None or reg_key == filter_key:
                    hit_counts[(reg_key, art_idx)] += 1

        if not hit_counts:
            return []

        matches: list[dict[str, Any]] = []
        for (reg_key, art_idx), score in hit_counts.items():
            reg = self._regulations[reg_key]
            article = reg["articles"][art_idx]
            matches.append(
                {
                    "regulation": reg_key,
                    "regulation_full_name": reg["full_name"],
                    "article_id": article["id"],
                    "title": article.get("title", ""),
                    "text": article.get("text", ""),
                    "topic": article.get("topic", ""),
                    "relevance_score": score,
                }
            )

        matches.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Store in bounded LRU cache – evict least-recently used entry when full
        if len(self._search_cache) >= self._search_cache_max:
            self._search_cache.popitem(last=False)  # remove LRU (oldest) entry
        self._search_cache[cache_key] = matches

        return matches

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
