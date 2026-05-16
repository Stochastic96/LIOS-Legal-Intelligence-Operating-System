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
    max_context_chars: int = 6000,
    lens: str | None = None,
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

    # Use lens-specific prompt when a lens is specified
    if lens:
        try:
            from lios.reasoning.lawyer_prompts import build_lens_prompt
            return build_lens_prompt(question, context_text, lens)
        except Exception:
            pass  # fall through to default IRAC prompt

    question_hint = _question_type_hint(question)

    return (
        "You are LIOS, a legal assistant specialising in EU and German law.\n\n"
        "STRICT RULES:\n"
        "- Answer ONLY using the provided legal context below.\n"
        "- The context may be written in German. Respond in the SAME language the user asked in.\n"
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


def build_direct_prompt(question: str, topic_area: str = "eu_regulatory") -> str:
    """Build a direct LLM prompt for easy questions that need no corpus context.

    Unlike :func:`build_prompt`, this does not supply a retrieved context block.
    Intended for DEFINITION and GENERAL questions where the LLM's training
    knowledge is sufficient. The caller should verify the answer with
    FactVerifier and fall back to the RAG path when the answer is not grounded.

    Args:
        question:    The user's legal question.
        topic_area:  ``"eu_regulatory"`` (default) for CSRD/ESRS/SFDR topics;
                     ``"general_law"`` for tort, contract, criminal, property law etc.
    """
    question_hint = _question_type_hint(question)

    if topic_area == "general_law":
        domain_instruction = (
            "You are LIOS, a legal assistant with broad knowledge of common law and civil law systems.\n\n"
            "INSTRUCTIONS:\n"
            "- Answer the question using your knowledge of general legal principles "
            "(tort law, contract law, criminal law, property law, company law, etc.).\n"
            "- When relevant, note how the principle varies across jurisdictions "
            "(e.g. English common law vs. German BGB vs. EU law).\n"
            "- Respond ONLY in English.\n"
            "- Do NOT invent case citations, article numbers, or specific statutes you are not confident about.\n"
            "- If you are uncertain, say so clearly.\n"
            "- Keep the answer clear, well-structured, and legally precise.\n\n"
        )
    else:
        domain_instruction = (
            "You are LIOS, a legal assistant specialising in EU and German law.\n\n"
            "INSTRUCTIONS:\n"
            "- Answer using your training knowledge of EU regulations (CSRD, ESRS, SFDR, "
            "EU Taxonomy, GDPR, and related directives).\n"
            "- Respond ONLY in English.\n"
            "- Do NOT invent specific article numbers or cite non-existent provisions.\n"
            "- If you are uncertain, say so clearly rather than guessing.\n"
            "- Keep the answer concise and factually accurate.\n\n"
        )

    return (
        f"{domain_instruction}"
        f"{question_hint}"
        f"Question:\n{question}\n"
    )


def _question_type_hint(question: str) -> str:
    """Return structured output instructions tailored to the detected question type."""
    q = question.lower()

    if any(kw in q for kw in ("what is", "define", "what does", "meaning of", "explain")):
        return (
            "RESPONSE GUIDANCE — Definition question.\n"
            "Structure your answer exactly as:\n"
            "**Definition**: [precise definition from the context in 1–2 sentences]\n"
            "**Legal Source**: [regulation + article citation]\n"
            "**Key Terms**: [bullet list of any important sub-terms or concepts]\n"
            "**Plain Language**: [one sentence accessible explanation]\n\n"
        )
    if any(kw in q for kw in ("applies to", "who must", "which compan", "subject to",
                               "applicable", "do we", "are we", "does it apply")):
        return (
            "RESPONSE GUIDANCE — Applicability question.\n"
            "Structure your answer exactly as:\n"
            "**Applicability**: [Yes / No / Conditional — one sentence verdict]\n"
            "**Threshold Criteria**: [bullet list: employee count, turnover, balance sheet, listing status]\n"
            "**Legal Basis**: [regulation + article citations]\n"
            "**Phase-In Timeline**: [which phase and from when, if phased regulation]\n"
            "**What This Means**: [plain-language consequence for the company]\n\n"
        )
    if any(kw in q for kw in ("penalty", "fine", "sanction", "non-compliance",
                               "what happens if", "consequence", "enforcement")):
        return (
            "RESPONSE GUIDANCE — Penalty question.\n"
            "Structure your answer exactly as:\n"
            "**Penalty Type**: [administrative fine / criminal / supervisory action]\n"
            "**Maximum Amount**: [specific amounts or ranges from the context]\n"
            "**Enforcement Authority**: [which body enforces this]\n"
            "**Legal Basis**: [regulation + article citations]\n"
            "**Risk Mitigation**: [1–2 bullet points on how to avoid the penalty]\n\n"
        )
    if any(kw in q for kw in ("when", "deadline", "timeline", "by when",
                               "phased", "financial year", "reporting period")):
        return (
            "RESPONSE GUIDANCE — Timeline question.\n"
            "Structure your answer exactly as:\n"
            "**Key Dates** (chronological order):\n"
            "- [date]: [milestone or obligation]\n"
            "- [date]: [milestone or obligation]\n"
            "**Legal Basis**: [regulation + article citations]\n"
            "**Action Required**: [what must be done by each date]\n\n"
        )
    if any(kw in q for kw in ("how to", "how do", "steps", "procedure", "process",
                               "implement", "comply", "get started")):
        return (
            "RESPONSE GUIDANCE — Procedural question.\n"
            "Structure your answer exactly as:\n"
            "**Step-by-step process** (numbered):\n"
            "1. [first action with legal reference]\n"
            "2. [second action]\n"
            "**Key Considerations**: [2–3 bullets on risks, timelines, or dependencies]\n"
            "**Legal Basis**: [regulation + article citations]\n\n"
        )
    if any(kw in q for kw in ("difference", "compare", "versus", " vs ", "distinguish",
                               "similarities", "overlap")):
        return (
            "RESPONSE GUIDANCE — Comparison question.\n"
            "Structure your answer exactly as:\n"
            "**[Regulation A]**: [scope and key obligation in 1–2 sentences]\n"
            "**[Regulation B]**: [scope and key obligation in 1–2 sentences]\n"
            "**Key Differences**: [bullet list of distinct obligations, scope, thresholds]\n"
            "**Overlap / Interaction**: [where the regulations interact or create dual obligations]\n\n"
        )
    if any(kw in q for kw in ("requirement", "must", "shall", "obligat", "what must",
                               "what are the", "disclosure", "report on")):
        return (
            "RESPONSE GUIDANCE — Requirements question.\n"
            "Structure your answer exactly as:\n"
            "**Core Obligations** (bullet list, each with source citation):\n"
            "- [obligation] — [CSRD Art.X / ESRS E1 §Y]\n"
            "**Scope**: [who these obligations apply to]\n"
            "**Reporting Format**: [where/how to disclose if specified in context]\n"
            "**Deadlines**: [relevant dates if mentioned]\n\n"
        )
    return (
        "RESPONSE GUIDANCE — General legal question.\n"
        "Structure your answer exactly as:\n"
        "**Summary**: [direct answer in 1–2 sentences]\n"
        "**Legal Basis**: [regulation + article citations]\n"
        "**Details**: [supporting explanation from the context]\n\n"
    )


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


def format_context_from_chunks(chunks: list[dict[str, Any]], max_chars: int = 6000) -> str:
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
