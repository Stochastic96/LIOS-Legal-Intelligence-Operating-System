"""LIOS entry point – exposes FastAPI app, Click CLI, and standalone RAG pipeline."""

from __future__ import annotations

import logging

from lios.api.routes import app
from lios.cli.interface import cli

__all__ = ["app", "cli", "generate_answer"]

logger = logging.getLogger(__name__)


def generate_answer(question: str) -> str:
    """Answer a legal question using the full LIOS RAG pipeline.

    The pipeline:
    1. Retrieves relevant legal chunks via :class:`~lios.retrieval.hybrid_retriever.HybridRetriever`
       (BM25 + semantic + grounded rerank).
    2. Builds a structured IRAC-style prompt via
       :func:`~lios.reasoning.legal_reasoner.build_prompt`.
    3. Sends the prompt to Ollama/Mistral and returns the answer.

    When Ollama is unavailable the function falls back gracefully to the
    rule-based :class:`~lios.orchestration.engine.OrchestrationEngine`.

    Args:
        question: The user's legal question in natural language.

    Returns:
        A string answer, structured as Issue / Rule / Analysis / Conclusion.
    """
    from lios.reasoning.legal_reasoner import build_prompt
    from lios.retrieval.hybrid_retriever import get_retriever

    retriever = get_retriever()
    top_chunks = retriever.search(question, top_k=5)

    if not top_chunks:
        return "No relevant legal context found in the corpus."

    # Build structured prompt using retrieved chunks (dicts with full metadata).
    raw_chunks = [rc.chunk for rc in top_chunks]
    prompt = build_prompt(question, raw_chunks)

    # Ollama may be unavailable (connection refused, model not found, timeout, etc.);
    # fall back gracefully rather than propagating a connectivity error to the caller.
    try:
        from lios.llm.ollama_client import call_ollama_sync

        return call_ollama_sync(prompt)
    except Exception as exc:  # noqa: BLE001 – intentional broad catch for LLM fallback
        logger.warning("Ollama unavailable (%s); falling back to rule-based engine.", exc)

    from lios.orchestration.engine import OrchestrationEngine

    engine = OrchestrationEngine()
    result = engine.route_query(question)
    return result.answer


if __name__ == "__main__":
    print("LIOS Legal Assistant Ready (type 'exit' or 'quit' to stop)")
    while True:
        try:
            q = input("\nAsk legal question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            break

        print("\n", generate_answer(q))

