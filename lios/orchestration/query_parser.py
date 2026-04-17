"""Query parser – extracts intent and entities from raw queries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedQuery:
    raw_query: str
    intent: str  # see INTENT_* constants below
    regulations: list[str]
    jurisdictions: list[str]
    company_profile: dict[str, Any]
    keywords: list[str]


# Intent constants
INTENT_APPLICABILITY = "applicability_check"
INTENT_ROADMAP = "compliance_roadmap"
INTENT_BREAKDOWN = "legal_breakdown"
INTENT_CONFLICT = "conflict_detection"
INTENT_GENERAL = "general_query"

# Keyword → regulation mapping
_REG_KEYWORDS: dict[str, str] = {
    "csrd": "CSRD",
    "corporate sustainability reporting": "CSRD",
    "sustainability reporting directive": "CSRD",
    "esrs": "ESRS",
    "european sustainability reporting": "ESRS",
    "taxonomy": "EU_TAXONOMY",
    "eu taxonomy": "EU_TAXONOMY",
    "green taxonomy": "EU_TAXONOMY",
    "dnsh": "EU_TAXONOMY",
    "sfdr": "SFDR",
    "sustainable finance disclosure": "SFDR",
    "article 8": "SFDR",
    "article 9": "SFDR",
    "article 6": "SFDR",
}

# Keyword → jurisdiction mapping
_JUR_KEYWORDS: dict[str, str] = {
    "germany": "Germany",
    "german": "Germany",
    "deutschland": "Germany",
    "hgb": "Germany",
    "france": "France",
    "french": "France",
    "netherlands": "Netherlands",
    "dutch": "Netherlands",
    "spain": "Spain",
    "spanish": "Spain",
    "austria": "Austria",
    "austrian": "Austria",
    "italy": "Italy",
    "italian": "Italy",
    "eu": "EU",
    "european union": "EU",
    "uk": "UK",
    "united kingdom": "UK",
}

# Intent patterns
_APPLICABILITY_PATTERNS = re.compile(
    r"\b(appl(y|ies|icable|ication)|in.scope|do we need|must we|are we subject|does .* apply|"
    r"threshold|qualify|who.* covered|which companies)\b",
    re.IGNORECASE,
)
_ROADMAP_PATTERNS = re.compile(
    r"\b(roadmap|steps?|plan|how to comply|compliance plan|what.* do|next steps?|action|"
    r"prepare|get ready|deadline)\b",
    re.IGNORECASE,
)
_BREAKDOWN_PATTERNS = re.compile(
    r"\b(breakdown|explain|what is|define|overview|summary|tell me about|describe|"
    r"obligation|penalty|penalt|sanction|timeline|when does)\b",
    re.IGNORECASE,
)
_CONFLICT_PATTERNS = re.compile(
    r"\b(conflict|gap|contradict|overlap|differ|national law|versus|vs\.?|tension|"
    r"inconsisten|hgb|pacte|wphg)\b",
    re.IGNORECASE,
)


class QueryParser:
    """Parse a raw query string into a structured ParsedQuery."""

    def parse(
        self,
        raw_query: str,
        context: dict[str, Any] | None = None,
    ) -> ParsedQuery:
        context = context or {}
        q = raw_query.lower()

        regulations = self._extract_regulations(q)
        jurisdictions = self._extract_jurisdictions(q)
        keywords = self._extract_keywords(q)
        intent = self._detect_intent(q)
        company_profile = self._extract_company_profile(q, context)

        return ParsedQuery(
            raw_query=raw_query,
            intent=intent,
            regulations=regulations,
            jurisdictions=jurisdictions,
            company_profile=company_profile,
            keywords=keywords,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_regulations(self, q: str) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        for kw, reg in _REG_KEYWORDS.items():
            if kw in q and reg not in seen:
                found.append(reg)
                seen.add(reg)
        return found

    def _extract_jurisdictions(self, q: str) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        for kw, jur in _JUR_KEYWORDS.items():
            if kw in q and jur not in seen:
                found.append(jur)
                seen.add(jur)
        return found

    def _extract_keywords(self, q: str) -> list[str]:
        # Remove stopwords and return meaningful tokens
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "up", "about", "into", "through",
            "our", "we", "us", "my", "i", "it", "its", "and", "or", "but", "if",
            "this", "that", "these", "those", "what", "how", "when", "where", "which",
        }
        tokens = re.findall(r"\b[a-z][a-z0-9]{2,}\b", q)
        return [t for t in tokens if t not in stopwords][:20]

    def _detect_intent(self, q: str) -> str:
        # Check more specific intents first
        if _ROADMAP_PATTERNS.search(q):
            return INTENT_ROADMAP
        if _CONFLICT_PATTERNS.search(q):
            return INTENT_CONFLICT
        if _APPLICABILITY_PATTERNS.search(q):
            return INTENT_APPLICABILITY
        if _BREAKDOWN_PATTERNS.search(q):
            return INTENT_BREAKDOWN
        return INTENT_GENERAL

    def _extract_company_profile(
        self, q: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        # Only pass through an explicitly provided company profile from context.
        # We deliberately do NOT parse employee counts, turnover, or jurisdiction
        # from free-text queries — company data should be provided explicitly when
        # the caller needs applicability or roadmap analysis.
        return dict(context.get("company_profile", {}))
