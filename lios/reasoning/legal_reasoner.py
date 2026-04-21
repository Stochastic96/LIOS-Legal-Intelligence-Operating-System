"""IRAC-structured legal prompt builder for grounded LLM responses.

IRAC (Issue -- Rule -- Analysis -- Conclusion) is the standard structure used in
common-law and civil-law legal writing.  The build_prompt function creates a
prompt that instructs the LLM to:

* Answer ONLY using the supplied context (no hallucination).
* Accept context in German (EU / BGB / GDPR texts) while always responding in English.
* Format the answer with the four IRAC sections.
* Cite the source of every legal rule it references.
* Adapt the response depth to the question type (definition, applicability,
  requirement, timeline, penalty, etc.).
"""

from __future__ import annotations

from typing import Any


def build_prompt(
    question: str,
    context: "str | list[Any]",
    max_context_chars: int = 4000,
) -> str:
    """Build a structured legal reasoning prompt using IRAC format.

    The prompt enforces grounded answers: the model must reason only from the
    provided context and use the Issue / Rule / Analysis / Conclusion structure
    common in legal practice.  A question-type hint is added to guide the model
    toward the most useful response format.

    Args:
        question:          The user's legal question (English).
        context:           Either a plain string of retrieved legal text, or a
                           list of text strings / dicts with a ``text`` key.
                           The context may be in German; the model is instructed
                           to respond in English regardless.
        max_context_chars: Soft character limit for the assembled context block
                           (only used when *context* is a list).

    Returns:
        A fully formatted prompt string ready to send to an LLM.
    """
    if isinstance(context, str):
        context_text = context.strip()
        if not context_text:
            context_text = "No legal context provided."
    else:
        context_text = _format_chunks(context, max_context_chars)

    question_hint = _question_type_hint(question)

    return (
        "You are LIOS, a legal assistant specialising in EU and German law.\n\n"
        "STRICT RULES:\n"
        "- Answer ONLY using the provided legal context below.\n"
        "- The context may be written in German. You MUST respond in English.\n"
        "- Do NOT invent laws, articles, or case references.\n"
        "- If the context does not contain enough information, say "
        "\"I don't know based on the provided context.\"\n"
        "- Preserve legal precision; do not paraphrase in ways that change meaning.\n"
        "- Cite the source document or section whenever you state a legal rule.\n\n"
        f"{question_hint}"
        "Use the following legal reasoning structure in your answer:\n\n"
        "1. Issue    -- What is the legal question being asked?\n"
        "2. Rule     -- Which legal provision(s) apply? Cite the source (e.g., GDPR Art. 6).\n"
        "3. Analysis -- Apply the rule(s) to the facts presented in the question.\n"
        "4. Conclusion -- State the legal outcome clearly and concisely.\n\n"
        "---\n"
        f"Legal Context:\n{context_text}\n\n"
        "---\n"
        f"Question:\n{question}\n"
    )


def _question_type_hint(question: str) -> str:
    """Return a short instruction paragraph tailored to the question type."""
    q = question.lower()

    if any(kw in q for kw in ("what is", "define", "what does", "meaning of")):
        return (
            "RESPONSE GUIDANCE: This is a definition question.  Provide a clear, "
            "precise definition drawn directly from the context.\n\n"
        )
    if any(kw in q for kw in ("applies to", "who must", "which compan", "subject to",
                               "applicable", "do we", "are we")):
        return (
            "RESPONSE GUIDANCE: This is an applicability question.  Identify the "
            "specific criteria (employee thresholds, turnover, listing status, etc.) "
            "from the context and state whether they apply.\n\n"
        )
    if any(kw in q for kw in ("penalty", "fine", "sanction", "non-compliance",
                               "what happens if", "consequence")):
        return (
            "RESPONSE GUIDANCE: This is a penalty question.  Focus on enforcement "
            "mechanisms, sanction levels, and the responsible enforcement authority "
            "as described in the context.\n\n"
        )
    if any(kw in q for kw in ("when", "deadline", "timeline", "by when",
                               "phased", "financial year")):
        return (
            "RESPONSE GUIDANCE: This is a timeline question.  Extract and clearly "
            "list all relevant dates and deadlines from the context in chronological "
            "order.\n\n"
        )
    if any(kw in q for kw in ("how to", "how do", "steps", "procedure", "process",
                               "implement", "comply")):
        return (
            "RESPONSE GUIDANCE: This is a procedural question.  Structure your "
            "answer as a numbered sequence of steps drawn from the context.\n\n"
        )
    if any(kw in q for kw in ("difference", "compare", "versus", " vs ", "distinguish")):
        return (
            "RESPONSE GUIDANCE: This is a comparison question.  Clearly contrast "
            "the two subjects along key dimensions (scope, obligations, timeline, etc.).\n\n"
        )
    if any(kw in q for kw in ("requirement", "must", "shall", "obligat", "what must",
                               "what are the", "disclosure")):
        return (
            "RESPONSE GUIDANCE: This is a requirements question.  List each "
            "obligation as a separate bullet point with its source citation.\n\n"
        )
    return ""


def _format_chunks(chunks: list[Any], max_chars: int) -> str:
    """Format a list of chunks into a context string respecting a char budget."""
    parts: list[str] = []
    total = 0
    for i, chunk in enumerate(chunks, start=1):
        if isinstance(chunk, dict):
            reg = chunk.get("regulation", "")
            article = chunk.get("article", "")
            title = chunk.get("title", "")
            text = chunk.get("text", "").strip()
            header = f"[{i}]"
            if reg:
                header += f" {reg}"
            if article:
                header += f" {article}"
            if title:
                header += f" -- {title}"
            source = chunk.get("source", "") or chunk.get("source_url", "")
            if source:
                header += f" (Source: {source})"
            entry = f"{header}\n{text}"
        else:
            entry = f"[{i}] {str(chunk).strip()}"

        if total + len(entry) > max_chars and parts:
            break
        parts.append(entry)
        total += len(entry)

    return "\n\n".join(parts) if parts else "No legal context provided."


def format_context_from_chunks(chunks: list[dict[str, Any]], max_chars: int = 4000) -> str:
    """Convert a list of retrieved chunk dicts into a labelled context string.

    Convenience wrapper around _format_chunks for callers that already
    have a list of dicts (e.g., results from lios.retrieval.retriever.retrieve).

    Args:
        chunks:    Chunk dicts with at least ``title``, ``text``, and ``source``.
        max_chars: Soft character limit; stops adding chunks once exceeded.

    Returns:
        Formatted multi-chunk context string.
    """
    return _format_chunks(chunks, max_chars)
