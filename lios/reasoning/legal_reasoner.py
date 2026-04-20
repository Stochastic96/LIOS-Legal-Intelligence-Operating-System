"""Legal reasoning prompt builder using the IRAC framework.

IRAC (Issue – Rule – Analysis – Conclusion) is the standard structure used in
common-law and civil-law legal writing.  The :func:`build_prompt` function
creates a prompt that instructs the LLM to:

* Answer **only** using the supplied context (no hallucination).
* Accept context in German (EU / BGB / GDPR texts) while always
  **responding in English**.
* Format the answer with the four IRAC sections.
* Cite the source of every legal rule it references.
"""

from __future__ import annotations

from typing import Any

_SYSTEM_INSTRUCTION = """\
You are LIOS, a Legal Intelligence Operating System.

STRICT RULES – follow them exactly:
1. Answer ONLY using the LEGAL CONTEXT provided below. Do NOT invent facts.
2. The context may be written in German. You MUST respond in English.
3. If the context does not contain enough information to answer, say:
   "The provided legal context does not contain sufficient information to answer this question."
4. Cite the source document or section whenever you state a legal rule.

Structure every answer using the IRAC framework:

Issue
-----
[State the legal question raised.]

Rule
----
[Identify the applicable legal rule(s) from the context, with citations.]

Analysis
--------
[Apply the rule(s) to the question step by step.]

Conclusion
----------
[State the legal conclusion clearly in one or two sentences.]
"""


def build_prompt(question: str, context: str) -> str:
    """Build a grounded IRAC prompt for the LLM.

    Args:
        question: The user's legal question (English).
        context:  Retrieved legal text, possibly in German.

    Returns:
        A single prompt string ready to be sent to an LLM.
    """
    context = context.strip() if context else ""
    question = question.strip()

    context_block = (
        f"LEGAL CONTEXT:\n{context}"
        if context
        else "LEGAL CONTEXT:\n[No relevant context found. Decline to answer.]"
    )

    return (
        f"{_SYSTEM_INSTRUCTION}\n"
        f"{'=' * 60}\n"
        f"{context_block}\n"
        f"{'=' * 60}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER (in English, using IRAC format):"
    )


def format_context_from_chunks(chunks: list[dict[str, Any]], max_chars: int = 4000) -> str:
    """Convert a list of retrieved chunk dicts into a labelled context string.

    Args:
        chunks:    Chunk dicts with at least ``title``, ``text``, and ``source``.
        max_chars: Soft character limit; stops adding chunks once exceeded.

    Returns:
        Formatted multi-chunk context string.
    """
    parts: list[str] = []
    total = 0
    for i, chunk in enumerate(chunks, start=1):
        title = chunk.get("title", "")
        text = chunk.get("text", "").strip()
        source = chunk.get("source", "")

        header = f"[{i}]"
        if title:
            header += f" {title}"
        if source:
            header += f" (Source: {source})"

        entry = f"{header}\n{text}"
        if total + len(entry) > max_chars and parts:
            break
        parts.append(entry)
        total += len(entry)

    return "\n\n".join(parts)
