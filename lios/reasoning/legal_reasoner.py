"""IRAC-structured legal prompt builder for grounded LLM responses."""

from __future__ import annotations

from typing import Any


def build_prompt(question: str, context_chunks: list[Any], max_context_chars: int = 4000) -> str:
    """Build a structured legal reasoning prompt using IRAC format.

    The prompt enforces grounded answers: the model must reason only from the
    provided context and use the Issue / Rule / Analysis / Conclusion structure
    common in legal practice.

    Args:
        question:         The user's legal question.
        context_chunks:   A list of text strings or dicts with a ``text`` key.
                          These are the retrieved legal passages to reason from.
        max_context_chars: Soft character limit for the assembled context block.

    Returns:
        A fully formatted prompt string ready to send to an LLM.
    """
    # Normalise chunks to strings, respecting the char budget.
    parts: list[str] = []
    total = 0
    for i, chunk in enumerate(context_chunks, start=1):
        if isinstance(chunk, dict):
            reg = chunk.get("regulation", "")
            article = chunk.get("article", "")
            title = chunk.get("title", "")
            text = chunk.get("text", "").strip()
            header = f"[{i}] {reg}"
            if article:
                header += f" {article}"
            if title:
                header += f" – {title}"
            entry = f"{header}\n{text}"
        else:
            entry = f"[{i}] {str(chunk).strip()}"

        if total + len(entry) > max_context_chars and parts:
            break
        parts.append(entry)
        total += len(entry)

    context = "\n\n".join(parts) if parts else "No legal context provided."

    return f"""You are LIOS, a legal assistant specialising in EU and German law.

STRICT RULES:
- Answer ONLY using the provided legal context below.
- Do NOT invent laws, articles, or case references.
- If the context does not contain enough information, say "I don't know based on the provided context."
- Preserve legal precision; do not paraphrase in ways that change meaning.

Use the following legal reasoning structure in your answer:

1. Issue    – What is the legal question being asked?
2. Rule     – Which legal provision(s) apply? Cite the source (e.g., GDPR Art. 6).
3. Analysis – Apply the rule(s) to the facts presented in the question.
4. Conclusion – State the legal outcome clearly and concisely.

---
Legal Context:
{context}

---
Question:
{question}
"""
