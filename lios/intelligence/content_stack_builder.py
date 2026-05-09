"""Content stack builder — auto-generates Q&A entries from lawyer-lens annotated chunks.

For each regulation ingested, this module reads the lens_tags from all chunks
and produces 10 standard Q&A entries covering the most common question types.

The builder is called automatically by the batch PDF importer. It can also be
run standalone to rebuild the stack from an existing corpus.

Usage::

    from lios.intelligence.content_stack_builder import build_stack_from_corpus
    entries = build_stack_from_corpus()   # reads data/corpus/legal_chunks.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lios.intelligence.content_stack import ContentStack, get_stack

_CORPUS_PATH = Path("data/corpus/legal_chunks.jsonl")

# ---------------------------------------------------------------------------
# Q-type builders — each takes (regulation, chunks) and returns an entry dict
# ---------------------------------------------------------------------------

_QTYPES = [
    "what_is",
    "who_affected",
    "scope_in",
    "scope_out",
    "what_required",
    "by_when",
    "penalties",
    "key_definitions",
    "interaction",
    "impact_summary",
]


def _agg(chunks: list[dict], lens: str, field: str, limit: int = 8) -> list[str]:
    """Aggregate unique items from lens_tags[lens][field] across chunks."""
    seen: set[str] = set()
    results: list[str] = []
    for chunk in chunks:
        items = (chunk.get("lens_tags", {}) or {}).get(lens, {}).get(field, [])
        for item in items:
            item = item.strip()
            if item and item not in seen:
                seen.add(item)
                results.append(item)
                if len(results) >= limit:
                    return results
    return results


def _citations(chunks: list[dict], limit: int = 6) -> list[str]:
    """Generate citation strings from a chunk list."""
    seen: set[str] = set()
    cites: list[str] = []
    for chunk in chunks:
        reg = chunk.get("regulation", "")
        art = chunk.get("article", "")
        if reg and art:
            c = f"{reg} {art}"
            if c not in seen:
                seen.add(c)
                cites.append(c)
                if len(cites) >= limit:
                    break
    return cites


def _bullet(items: list[str], max_items: int = 5) -> str:
    if not items:
        return "_No specific information found in indexed text._"
    return "\n".join(f"- {i}" for i in items[:max_items])


def _build_what_is(regulation: str, chunks: list[dict]) -> dict:
    defs = _agg(chunks, "drafter", "definitions", 4)
    scope_in = _agg(chunks, "drafter", "scope_in", 3)
    purposes = _agg(chunks, "interpretive", "purposive_hints", 2)

    parts: list[str] = []
    if defs:
        parts.append(_bullet(defs, 3))
    elif scope_in:
        parts.append(_bullet(scope_in, 3))
    if purposes:
        parts.append("\n**Legislative Intent:**\n" + _bullet(purposes, 2))

    answer = parts[0] if parts else f"_{regulation} is a legal instrument. Upload the official PDF to generate a detailed answer._"
    return _entry(regulation, "drafter", "what_is",
                  f"What is {regulation}?", answer, chunks, 0.85)


def _build_who_affected(regulation: str, chunks: list[dict]) -> dict:
    entities = _agg(chunks, "impact", "affected_entities", 8)
    thresholds = _agg(chunks, "compliance", "thresholds", 5)
    triggers = _agg(chunks, "compliance", "triggers", 3)

    parts: list[str] = []
    if entities:
        parts.append("**Affected Entity Types:**\n" + _bullet(entities, 6))
    if thresholds:
        parts.append("**Applicability Thresholds:**\n" + _bullet(thresholds, 4))
    if triggers:
        parts.append("**Triggering Conditions:**\n" + _bullet(triggers, 3))

    answer = "\n\n".join(parts) if parts else f"_Upload the {regulation} PDF for detailed applicability information._"
    return _entry(regulation, "impact", "who_affected",
                  f"Who must comply with {regulation}?", answer, chunks, 0.9)


def _build_scope_in(regulation: str, chunks: list[dict]) -> dict:
    scope = _agg(chunks, "drafter", "scope_in", 6)
    thresholds = _agg(chunks, "compliance", "thresholds", 4)

    parts: list[str] = []
    if scope:
        parts.append("**Scope (in):**\n" + _bullet(scope, 5))
    if thresholds:
        parts.append("**Size Thresholds:**\n" + _bullet(thresholds, 4))

    answer = "\n\n".join(parts) if parts else "_Scope information not yet extracted from this regulation._"
    return _entry(regulation, "drafter", "scope_in",
                  f"Which companies are in scope of {regulation}?", answer, chunks, 0.85)


def _build_scope_out(regulation: str, chunks: list[dict]) -> dict:
    scope_out = _agg(chunks, "drafter", "scope_out", 6)
    exceptions = _agg(chunks, "drafter", "exceptions", 4)

    parts: list[str] = []
    if scope_out:
        parts.append("**Exemptions:**\n" + _bullet(scope_out, 5))
    if exceptions:
        parts.append("**Exceptions / Derogations:**\n" + _bullet(exceptions, 4))

    answer = "\n\n".join(parts) if parts else "_No specific exemptions found in indexed text._"
    return _entry(regulation, "drafter", "scope_out",
                  f"Who is exempt from {regulation}?", answer, chunks, 0.85)


def _build_what_required(regulation: str, chunks: list[dict]) -> dict:
    obligations = _agg(chunks, "compliance", "obligations", 8)
    actions = _agg(chunks, "impact", "required_actions", 5)

    # Deduplicate between obligations and actions
    seen: set[str] = set()
    combined: list[str] = []
    for item in obligations + actions:
        if item not in seen:
            seen.add(item)
            combined.append(item)

    answer = "**Core Obligations:**\n" + _bullet(combined, 6) if combined else "_No specific obligations found in indexed text._"
    return _entry(regulation, "compliance", "what_required",
                  f"What must companies do under {regulation}?", answer, chunks, 0.9)


def _build_by_when(regulation: str, chunks: list[dict]) -> dict:
    timelines = _agg(chunks, "compliance", "timelines", 8)
    deadlines = _agg(chunks, "impact", "deadlines", 5)

    seen: set[str] = set()
    combined: list[str] = []
    for item in timelines + deadlines:
        if item not in seen:
            seen.add(item)
            combined.append(item)

    answer = "**Key Dates and Deadlines:**\n" + _bullet(combined, 6) if combined else "_No specific timeline information found in indexed text._"
    return _entry(regulation, "compliance", "by_when",
                  f"What are the key deadlines for {regulation}?", answer, chunks, 0.85)


def _build_penalties(regulation: str, chunks: list[dict]) -> dict:
    penalties = _agg(chunks, "risk", "penalties", 6)
    amounts = _agg(chunks, "risk", "max_amounts", 4)
    bodies = _agg(chunks, "risk", "enforcement_bodies", 4)
    liability = _agg(chunks, "risk", "liability_phrases", 3)

    parts: list[str] = []
    if penalties:
        parts.append("**Penalty Provisions:**\n" + _bullet(penalties, 4))
    if amounts:
        parts.append("**Maximum Amounts:**\n" + _bullet(amounts, 4))
    if bodies:
        parts.append("**Enforcement Authorities:**\n" + _bullet(bodies, 3))
    if liability:
        parts.append("**Liability:**\n" + _bullet(liability, 3))

    answer = "\n\n".join(parts) if parts else "_No specific penalty information found in indexed text._"
    return _entry(regulation, "risk", "penalties",
                  f"What are the penalties for non-compliance with {regulation}?", answer, chunks, 0.9)


def _build_key_definitions(regulation: str, chunks: list[dict]) -> dict:
    defs = _agg(chunks, "drafter", "definitions", 10)

    answer = "**Key Defined Terms:**\n" + _bullet(defs, 8) if defs else "_No formal definitions found in indexed text._"
    return _entry(regulation, "drafter", "key_definitions",
                  f"What are the key definitions in {regulation}?", answer, chunks, 0.9)


def _build_interaction(regulation: str, chunks: list[dict]) -> dict:
    principles = _agg(chunks, "interpretive", "legal_principles", 4)
    conflicts = _agg(chunks, "interpretive", "conflicts", 4)
    refs = _agg(chunks, "interpretive", "precedent_refs", 6)

    parts: list[str] = []
    if principles:
        parts.append("**Legal Principles:**\n" + _bullet(principles, 3))
    if conflicts:
        parts.append("**Derogations / Conflicts:**\n" + _bullet(conflicts, 3))
    if refs:
        parts.append("**Cross-References:**\n" + _bullet(refs, 5))

    answer = "\n\n".join(parts) if parts else "_No cross-reference information found in indexed text._"
    return _entry(regulation, "interpretive", "interaction",
                  f"How does {regulation} interact with related regulations?", answer, chunks, 0.75)


def _build_impact_summary(regulation: str, chunks: list[dict]) -> dict:
    entities = _agg(chunks, "impact", "affected_entities", 5)
    actions = _agg(chunks, "impact", "required_actions", 4)
    deadlines = _agg(chunks, "impact", "deadlines", 3)
    new_obs = _agg(chunks, "impact", "new_obligations", 3)

    parts: list[str] = []
    if entities:
        parts.append("**Who Is Affected:**\n" + _bullet(entities, 4))
    if actions:
        parts.append("**What Must Change:**\n" + _bullet(actions, 4))
    if deadlines:
        parts.append("**Key Deadlines:**\n" + _bullet(deadlines, 3))
    if new_obs:
        parts.append("**New Obligations:**\n" + _bullet(new_obs, 3))

    answer = "\n\n".join(parts) if parts else "_Upload the {regulation} PDF for a detailed impact summary._"
    return _entry(regulation, "impact", "impact_summary",
                  f"What is the business impact of {regulation}?", answer, chunks, 0.85)


_BUILDER_MAP = {
    "what_is":         _build_what_is,
    "who_affected":    _build_who_affected,
    "scope_in":        _build_scope_in,
    "scope_out":       _build_scope_out,
    "what_required":   _build_what_required,
    "by_when":         _build_by_when,
    "penalties":       _build_penalties,
    "key_definitions": _build_key_definitions,
    "interaction":     _build_interaction,
    "impact_summary":  _build_impact_summary,
}


def _entry(
    regulation: str,
    lens: str,
    qtype: str,
    question: str,
    answer: str,
    chunks: list[dict],
    confidence: float,
) -> dict[str, Any]:
    return {
        "key":              f"{regulation}|{lens}|{qtype}",
        "regulation":       regulation,
        "lens":             lens,
        "qtype":            qtype,
        "question":         question,
        "answer":           answer,
        "citations":        _citations(chunks),
        "confidence":       confidence,
        "source_chunk_ids": [c.get("chunk_id", "") for c in chunks[:6] if c.get("chunk_id")],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_entries_for_regulation(regulation: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate all 10 standard Q&A entries for a regulation from its chunks."""
    entries: list[dict[str, Any]] = []
    for qtype, builder_fn in _BUILDER_MAP.items():
        try:
            entry = builder_fn(regulation, chunks)
            entries.append(entry)
        except Exception:
            pass
    return entries


def build_stack_from_corpus(
    corpus_path: str | Path = _CORPUS_PATH,
    stack: ContentStack | None = None,
    save: bool = True,
) -> int:
    """Read all chunks from corpus, build entries per regulation, save stack.

    Returns number of entries generated.
    """
    corpus_path = Path(corpus_path)
    if stack is None:
        stack = get_stack()

    # Load all chunks
    all_chunks: dict[str, list[dict]] = {}
    if corpus_path.exists():
        for line in corpus_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                reg = chunk.get("regulation", "UNKNOWN")
                all_chunks.setdefault(reg, []).append(chunk)
            except json.JSONDecodeError:
                continue

    total = 0
    for regulation, chunks in all_chunks.items():
        if len(chunks) < 2:
            continue
        entries = build_entries_for_regulation(regulation, chunks)
        stack.add_entries(entries)
        total += len(entries)

    if save:
        stack.save()

    return total
