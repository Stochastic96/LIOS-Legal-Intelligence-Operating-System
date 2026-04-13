"""Regulatory database – loads and indexes all regulations."""

from __future__ import annotations

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
        self._load_all()

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
        """Keyword search over article texts.

        Returns list of matches sorted by relevance (number of keyword hits).
        """
        keywords = [w.lower() for w in query.split() if len(w) > 2]
        if not keywords:
            return []

        regulations_to_search: list[str]
        if regulation:
            key = self._resolve_key(regulation)
            regulations_to_search = [key] if key in self._regulations else []
        else:
            regulations_to_search = list(self._regulations.keys())

        matches: list[dict[str, Any]] = []
        for reg_key in regulations_to_search:
            reg = self._regulations[reg_key]
            for article in reg["articles"]:
                text = (
                    article.get("text", "") + " " + article.get("title", "") + " " + article.get("topic", "")
                ).lower()
                score = sum(1 for kw in keywords if kw in text)
                if score > 0:
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
