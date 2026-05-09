"""Content stack — instant pre-built Q&A lookup, no LLM or retrieval required.

Every regulation that has been ingested through the lawyer-lens pipeline gets
10 standard Q&A entries covering the most common question types. These are
stored in ``data/memory/content_stack.json`` and loaded into memory at startup.

Lookup is O(1) by exact key, or O(n) keyword-scan for fuzzy matching.
Typical response time: < 1 ms.

Entry schema
------------
{
    "key":              "CSRD|impact|who_affected",
    "regulation":       "CSRD",
    "lens":             "impact",
    "qtype":            "who_affected",
    "question":         "Who must comply with CSRD?",
    "answer":           "...",
    "citations":        ["CSRD Art.2", "CSRD Art.3"],
    "confidence":       1.0,
    "source_chunk_ids": ["71bc4a88"]
}

Q-type taxonomy
---------------
who_affected    — Who must comply with {reg}?
what_required   — What must companies do under {reg}?
by_when         — What are the key deadlines for {reg}?
penalties       — What are the penalties for non-compliance with {reg}?
what_is         — What is {reg}?
scope_in        — Which companies are in scope of {reg}?
scope_out       — Who is exempt from {reg}?
key_definitions — What are the key definitions in {reg}?
interaction     — How does {reg} interact with related regulations?
impact_summary  — What is the business impact of {reg}?
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

_STACK_FILE = Path("data/memory/content_stack.json")
_lock = threading.Lock()

# Q-type keyword mapping — used for fuzzy lookup
_QTYPE_KEYWORDS: dict[str, list[str]] = {
    "who_affected":    ["who must", "who has to", "who needs to", "which companies", "does it apply", "subject to"],
    "what_required":   ["what must", "what are the requirements", "what are the obligations", "what do companies"],
    "by_when":         ["by when", "deadline", "timeline", "when must", "when does", "key dates", "phase-in"],
    "penalties":       ["penalty", "penalties", "fine", "fines", "sanction", "non-compliance", "enforcement", "what happens if"],
    "what_is":         ["what is", "what are", "define", "definition", "explain"],
    "scope_in":        ["in scope", "which entities", "who is covered", "applies to", "covered by"],
    "scope_out":       ["exempt", "exclusion", "not apply", "out of scope", "not covered", "exception"],
    "key_definitions": ["definition of", "key terms", "defined as", "means", "glossary"],
    "interaction":     ["interact", "relationship", "alongside", "compare", "overlap", "connection", "difference between"],
    "impact_summary":  ["impact", "business impact", "what changes", "practical", "effect", "consequence"],
}


class ContentStack:
    """In-memory lookup table for pre-built legal Q&A pairs."""

    def __init__(self, stack_file: str | Path = _STACK_FILE) -> None:
        self._file = Path(stack_file)
        self._entries: list[dict[str, Any]] = []
        self._index: dict[str, dict[str, Any]] = {}  # key → entry
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load entries from disk. Safe to call multiple times."""
        with _lock:
            if self._file.exists():
                try:
                    data = json.loads(self._file.read_text(encoding="utf-8"))
                    self._entries = data if isinstance(data, list) else []
                except Exception:
                    self._entries = []
            else:
                self._entries = []
            self._rebuild_index()

    def save(self) -> None:
        """Persist current entries to disk."""
        with _lock:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._file.write_text(
                json.dumps(self._entries, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def _rebuild_index(self) -> None:
        self._index = {e["key"]: e for e in self._entries if "key" in e}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_entry(self, entry: dict[str, Any]) -> None:
        """Add or replace an entry. Thread-safe."""
        key = entry.get("key") or f"{entry.get('regulation')}|{entry.get('lens')}|{entry.get('qtype')}"
        entry["key"] = key
        with _lock:
            self._index[key] = entry
            self._entries = list(self._index.values())

    def add_entries(self, entries: list[dict[str, Any]]) -> None:
        for e in entries:
            self.add_entry(e)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def lookup(self, regulation: str, qtype: str) -> dict[str, Any] | None:
        """Exact lookup by regulation + qtype. Returns first matching entry."""
        for lens in ("compliance", "risk", "drafter", "impact", "interpretive"):
            key = f"{regulation}|{lens}|{qtype}"
            entry = self._index.get(key)
            if entry:
                return entry
        # Try without lens prefix
        for entry in self._entries:
            if entry.get("regulation") == regulation and entry.get("qtype") == qtype:
                return entry
        return None

    def lookup_any(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Keyword-based fuzzy lookup across all entries. Returns up to top_k hits."""
        q = query.lower()
        scored: list[tuple[float, dict[str, Any]]] = []

        for entry in self._entries:
            score = _score_entry(q, entry)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def is_hit(self, query: str) -> bool:
        """True if at least one entry matches the query with confidence ≥ 0.5."""
        hits = self.lookup_any(query, top_k=1)
        return bool(hits) and hits[0].get("confidence", 0) >= 0.5

    def get_by_regulation(self, regulation: str) -> list[dict[str, Any]]:
        """Return all entries for a regulation."""
        return [e for e in self._entries if e.get("regulation", "").upper() == regulation.upper()]

    def all_regulations(self) -> list[str]:
        """Return sorted list of regulations in the stack."""
        return sorted({e.get("regulation", "") for e in self._entries if e.get("regulation")})

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_reg: dict[str, int] = {}
        for e in self._entries:
            reg = e.get("regulation", "UNKNOWN")
            by_reg[reg] = by_reg.get(reg, 0) + 1
        return {
            "total_entries": len(self._entries),
            "regulations":   len(by_reg),
            "by_regulation": dict(sorted(by_reg.items())),
        }


# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------


def _score_entry(query: str, entry: dict[str, Any]) -> float:
    """Score an entry against a lowercase query string. Returns 0.0–1.0."""
    score = 0.0
    reg = entry.get("regulation", "").lower()
    qtype = entry.get("qtype", "")
    question = entry.get("question", "").lower()
    answer = entry.get("answer", "").lower()

    # Regulation name match
    if reg and reg in query:
        score += 0.4

    # Q-type keyword match
    keywords = _QTYPE_KEYWORDS.get(qtype, [])
    for kw in keywords:
        if kw in query:
            score += 0.3
            break

    # Question text similarity (simple token overlap)
    q_tokens = set(re.findall(r"\b\w{4,}\b", query))
    entry_tokens = set(re.findall(r"\b\w{4,}\b", question + " " + answer[:200]))
    if q_tokens and entry_tokens:
        overlap = len(q_tokens & entry_tokens) / max(len(q_tokens), 1)
        score += overlap * 0.3

    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_stack_singleton: ContentStack | None = None
_stack_lock = threading.Lock()


def get_stack() -> ContentStack:
    """Return the module-level ContentStack singleton (lazy-loaded)."""
    global _stack_singleton
    if _stack_singleton is None:
        with _stack_lock:
            if _stack_singleton is None:
                _stack_singleton = ContentStack()
    return _stack_singleton


def format_stack_answer(entry: dict[str, Any]) -> str:
    """Format a content stack entry into a markdown answer string."""
    reg = entry.get("regulation", "")
    qtype = entry.get("qtype", "")
    answer = entry.get("answer", "")
    citations = entry.get("citations", [])
    lens = entry.get("lens", "")
    confidence = entry.get("confidence", 1.0)

    lens_label = {
        "compliance":   "Compliance Officer",
        "risk":         "Risk Manager",
        "drafter":      "Legal Drafter",
        "impact":       "Business Advisor",
        "interpretive": "Legal Advocate",
    }.get(lens, "LIOS")

    header = f"**{reg} — {qtype.replace('_', ' ').title()}**"
    if lens:
        header += f" *(perspective: {lens_label})*"

    cite_line = ""
    if citations:
        cite_line = "\n\n**Sources**: " + " · ".join(citations)

    confidence_note = ""
    if confidence < 0.8:
        confidence_note = "\n\n*Note: This answer is derived from extracted text — verify against the full document.*"

    return f"{header}\n\n{answer}{cite_line}{confidence_note}\n\n---\n*Answered instantly from LIOS content stack*"
