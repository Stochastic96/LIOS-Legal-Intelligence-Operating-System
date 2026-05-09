"""Lawyer-lens annotator — tags each chunk with structured metadata from 5 analytical perspectives.

Called at ingestion time so every chunk in legal_chunks.jsonl carries precomputed
lens_tags. Query time overhead: zero — all extraction is done once when the PDF is indexed.

Lenses
------
compliance   — obligations, thresholds, timelines, triggers
risk         — penalties, enforcement bodies, liability, monetary amounts
drafter      — exact definitions, scope inclusions/exclusions, exceptions
impact       — affected entities, required actions, deadlines, new obligations
interpretive — legal principles, precedent refs, conflicts, purposive hints
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# ── Compliance lens ──────────────────────────────────────────────────────────
_OBLIGATION_RE = re.compile(
    r"[^.]*\b(shall|must|is\s+required\s+to|are\s+required\s+to|have\s+to|"
    r"need\s+to|obligation\s+to|is\s+obliged\s+to|are\s+obliged\s+to|"
    r"mandatory)[^.]*\.",
    re.IGNORECASE,
)
_THRESHOLD_RE = re.compile(
    r"[^.]*\b(\d[\d\s,.]*\s*(employees?|staff|workers?)|"
    r"€\s*[\d,.]+\s*(million|billion|bn|m\b)|"
    r"net\s+turn[\-\s]?over|balance[\-\s]?sheet\s+total|"
    r"average\s+number\s+of\s+employees?|"
    r">?\s*\d[\d\s,.]*\s*employees?|"
    r">?\s*€\s*[\d,.]+)[^.]*\.",
    re.IGNORECASE,
)
_TIMELINE_RE = re.compile(
    r"[^.]*\b(by\s+\d{1,2}\s+\w+\s+\d{4}|"
    r"from\s+(?:fy\s*)?\d{4}|"
    r"by\s+\d{4}|"
    r"financial\s+year\s+\d{4}|"
    r"no\s+later\s+than|"
    r"\d{1,2}\s+(?:january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\s+\d{4}|"
    r"(?:20[2-4]\d))[^.]*\.",
    re.IGNORECASE,
)
_TRIGGER_RE = re.compile(
    r"[^.]*\b(where\s+(?:a\s+)?(?:member\s+state|undertaking|company|entity)|"
    r"subject\s+to\s+this|applicable\s+to|in\s+cases?\s+where|"
    r"if\s+(?:the|a|an|such)\s+\w+|provided\s+that|"
    r"where\s+applicable|when\s+(?:the|a|an)\s+\w+)[^.]*\.",
    re.IGNORECASE,
)

# ── Risk lens ────────────────────────────────────────────────────────────────
_PENALTY_RE = re.compile(
    r"[^.]*\b(penalt(?:y|ies)|fine[s]?|sanction[s]?|dissuasive|"
    r"administrative\s+measure|infringement|non.compliance|"
    r"enforcement\s+action|shall\s+be\s+subject\s+to)[^.]*\.",
    re.IGNORECASE,
)
_ENFORCEMENT_BODY_RE = re.compile(
    r"\b(supervisory\s+authorit(?:y|ies)|competent\s+authorit(?:y|ies)|"
    r"member\s+state[s]?|national\s+authorit(?:y|ies)|"
    r"european\s+commission|esma|eba|eiopa|bafin|"
    r"data\s+protection\s+authorit(?:y|ies)|auditor|"
    r"independent\s+assurance\s+provider)[^.]*\.",
    re.IGNORECASE,
)
_LIABILITY_RE = re.compile(
    r"[^.]*\b(liab(?:le|ility)|responsibl(?:e|ility)|indemnif(?:y|ication)|"
    r"compensat(?:e|ion|ory)|remedy|redress|damage[s]?)[^.]*\.",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(
    r"(?:€|EUR|%)\s*[\d,.]+\s*(?:million|billion|bn|m\b)?|"
    r"[\d,.]+\s*(?:million|billion|bn)\s*(?:€|EUR)|"
    r"\d+\s*%\s+of\s+(?:annual|global|total|worldwide)?\s*(?:net\s+)?turnover",
    re.IGNORECASE,
)

# ── Drafter lens ─────────────────────────────────────────────────────────────
_DEFINITION_RE = re.compile(
    r"[^.]*(?:‘[^']+’\s+means|"
    r"'[^']+'\s+means|"
    r'"[^"]+"\s+means|'
    r"for\s+the\s+purposes?\s+of\s+this|"
    r"(?:is|are)\s+defined?\s+(?:as|to\s+mean)|"
    r"the\s+term\s+‘[^']+’)[^.]*\.",
    re.IGNORECASE,
)
_SCOPE_IN_RE = re.compile(
    r"[^.]*\b(this\s+(?:regulation|directive|law|article)\s+(?:shall\s+)?applies?\s+to|"
    r"covered\s+by\s+this|shall\s+apply\s+to|"
    r"within\s+the\s+scope\s+of\s+this|"
    r"subject\s+to\s+this\s+(?:regulation|directive))[^.]*\.",
    re.IGNORECASE,
)
_SCOPE_OUT_RE = re.compile(
    r"[^.]*\b(shall\s+not\s+apply|does\s+not\s+apply|not\s+subject\s+to|"
    r"exempt(?:ed)?\s+from|excluded?\s+from\s+the\s+scope|"
    r"outside\s+the\s+scope|not\s+covered\s+by)[^.]*\.",
    re.IGNORECASE,
)
_EXCEPTION_RE = re.compile(
    r"[^.]*\b(except(?:ion)?(?:\s+where)?|unless|"
    r"by\s+way\s+of\s+derogation|notwithstanding|"
    r"in\s+derogation\s+of|without\s+prejudice\s+to)[^.]*\.",
    re.IGNORECASE,
)

# ── Impact lens ──────────────────────────────────────────────────────────────
_ENTITY_RE = re.compile(
    r"\b(large\s+undertaking[s]?|small\s+and\s+medium[\-\s]?(?:sized\s+)?enterprise[s]?|"
    r"SME[s]?|listed\s+compan(?:y|ies)|financial\s+market\s+participant[s]?|"
    r"investment\s+firm[s]?|credit\s+institution[s]?|insurance\s+undertaking[s]?|"
    r"non[\-\s]?EU\s+(?:parent\s+)?(?:company|undertaking)|"
    r"public[\-\s]?interest\s+entit(?:y|ies)|PIE[s]?|"
    r"third[\-\s]?country\s+(?:company|undertaking)|"
    r"upstream\s+(?:supplier[s]?|entity)|downstream\s+(?:partner[s]?|entity))\b",
    re.IGNORECASE,
)
_NEW_OBLIGATION_RE = re.compile(
    r"[^.]*\b(new\s+(?:obligation|requirement|duty|rule)|"
    r"for\s+the\s+first\s+time|additionally\s+(?:required|required)|"
    r"from\s+(?:fy\s*)?\d{4}(?:\s+onwards?)?|"
    r"entering\s+into\s+force|newly\s+(?:introduced|imposed|required))[^.]*\.",
    re.IGNORECASE,
)

# ── Interpretive lens ────────────────────────────────────────────────────────
_PRINCIPLE_RE = re.compile(
    r"[^.]*\b(principle\s+of\s+\w+|in\s+accordance\s+with|consistent\s+with|"
    r"pursuant\s+to\s+(?:article|art\.?)|in\s+conformity\s+with|"
    r"proportionality|subsidiarity|legal\s+certainty|good\s+faith|"
    r"legitimate\s+expectation)[^.]*\.",
    re.IGNORECASE,
)
_PRECEDENT_RE = re.compile(
    r"\b(?:art(?:icle)?\.?\s*\d+(?:[a-z])?(?:\s*\(\d+\))?|"
    r"recital\s+\d+|"
    r"case\s+C[-–]\d+/\d+|"
    r"annex\s+(?:[IVX]+|\d+)|"
    r"paragraph\s+\d+)\b",
    re.IGNORECASE,
)
_CONFLICT_RE = re.compile(
    r"[^.]*\b(notwithstanding|in\s+derogation\s+of|regardless\s+of|"
    r"without\s+prejudice\s+to|irrespective\s+of|"
    r"shall\s+prevail\s+over|takes?\s+precedence\s+over|"
    r"in\s+conflict\s+with)[^.]*\.",
    re.IGNORECASE,
)
_RECITAL_RE = re.compile(
    r"\bwhereas\b[^;]*;|"
    r"\(\d+\)\s+[A-Z][^.]{30,}\.",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------

_SENT_SPLIT_RE = re.compile(r"(?<=[.;?!])\s+(?=[A-Z\(])")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT_RE.split(text) if s.strip()]


def _match_sentences(text: str, pattern: re.Pattern) -> list[str]:
    """Return unique sentences matching pattern (max 8 per chunk)."""
    seen: set[str] = set()
    results: list[str] = []
    for sent in _sentences(text):
        if pattern.search(sent) and sent not in seen:
            seen.add(sent)
            results.append(sent)
            if len(results) >= 8:
                break
    return results


def _findall_unique(text: str, pattern: re.Pattern) -> list[str]:
    """Return unique non-empty matches (max 10)."""
    seen: set[str] = set()
    results: list[str] = []
    for m in pattern.finditer(text):
        val = m.group(0).strip()
        if val and val not in seen:
            seen.add(val)
            results.append(val)
            if len(results) >= 10:
                break
    return results


# ---------------------------------------------------------------------------
# Lens extractors
# ---------------------------------------------------------------------------


def _extract_compliance(text: str) -> dict[str, list[str]]:
    return {
        "obligations": _match_sentences(text, _OBLIGATION_RE),
        "thresholds":  _match_sentences(text, _THRESHOLD_RE),
        "timelines":   _match_sentences(text, _TIMELINE_RE),
        "triggers":    _match_sentences(text, _TRIGGER_RE),
    }


def _extract_risk(text: str) -> dict[str, list[str]]:
    return {
        "penalties":          _match_sentences(text, _PENALTY_RE),
        "enforcement_bodies": _findall_unique(text, _ENFORCEMENT_BODY_RE),
        "liability_phrases":  _match_sentences(text, _LIABILITY_RE),
        "max_amounts":        _findall_unique(text, _AMOUNT_RE),
    }


def _extract_drafter(text: str) -> dict[str, list[str]]:
    return {
        "definitions": _match_sentences(text, _DEFINITION_RE),
        "scope_in":    _match_sentences(text, _SCOPE_IN_RE),
        "scope_out":   _match_sentences(text, _SCOPE_OUT_RE),
        "exceptions":  _match_sentences(text, _EXCEPTION_RE),
    }


def _extract_impact(text: str) -> dict[str, list[str]]:
    return {
        "affected_entities":  _findall_unique(text, _ENTITY_RE),
        "required_actions":   _match_sentences(text, _OBLIGATION_RE),
        "deadlines":          _match_sentences(text, _TIMELINE_RE),
        "new_obligations":    _match_sentences(text, _NEW_OBLIGATION_RE),
    }


def _extract_interpretive(text: str) -> dict[str, list[str]]:
    return {
        "legal_principles": _match_sentences(text, _PRINCIPLE_RE),
        "precedent_refs":   _findall_unique(text, _PRECEDENT_RE),
        "conflicts":        _match_sentences(text, _CONFLICT_RE),
        "purposive_hints":  _match_sentences(text, _RECITAL_RE),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def annotate_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    """Add ``lens_tags`` dict to *chunk* in-place. Returns *chunk*.

    Safe to call on any chunk dict — if ``text`` is missing or empty, all
    lens arrays will be empty lists (no exception raised).
    """
    text = chunk.get("text", "") or ""
    chunk["lens_tags"] = {
        "compliance":   _extract_compliance(text),
        "risk":         _extract_risk(text),
        "drafter":      _extract_drafter(text),
        "impact":       _extract_impact(text),
        "interpretive": _extract_interpretive(text),
    }
    return chunk


def annotate_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate a list of chunks in-place. Returns the same list."""
    for chunk in chunks:
        annotate_chunk(chunk)
    return chunks
