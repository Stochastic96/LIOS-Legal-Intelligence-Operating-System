"""LIOS entry point -- exposes FastAPI app, Click CLI, and standalone pipelines.

Two standalone pipeline functions are available (no API server required):

``generate_answer(question)`` -- BM25/semantic hybrid retrieval (always available)::

    from lios.main import generate_answer
    print(generate_answer("What is a breach of contract?"))

``run_pipeline(question)`` -- FAISS dense retrieval (requires lios[data])::

    from lios.main import run_pipeline
    result = run_pipeline("What rights does GDPR give to data subjects?")
    print(result["answer"])
"""

from __future__ import annotations

import logging
from typing import Any

from lios.api.routes import app
from lios.cli.interface import cli
from lios.llm.ollama_client import OLLAMA_MODEL

logger = logging.getLogger(__name__)

__all__ = ["app", "cli", "generate_answer", "run_pipeline"]


# ---------------------------------------------------------------------------
# Pipeline 1 -- Hybrid BM25/semantic retrieval (no optional deps required)
# ---------------------------------------------------------------------------


def generate_answer(question: str) -> str:
    """Answer a legal question using the full LIOS RAG pipeline.

    The pipeline:
    1. Retrieves relevant legal chunks via HybridRetriever
       (BM25 + semantic + grounded rerank).
    2. Builds a structured IRAC-style prompt via build_prompt.
    3. Sends the prompt to Ollama/Mistral and returns the answer.

    When Ollama is unavailable the function falls back gracefully to the
    rule-based OrchestrationEngine.

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

    raw_chunks = [rc.chunk for rc in top_chunks]
    prompt = build_prompt(question, raw_chunks)

    try:
        from lios.llm.ollama_client import call_ollama_sync

        return call_ollama_sync(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama unavailable (%s); falling back to rule-based engine.", exc)

    from lios.orchestration.engine import OrchestrationEngine

    engine = OrchestrationEngine()
    result = engine.route_query(question)
    return result.answer


# ---------------------------------------------------------------------------
# Pipeline 2 -- FAISS dense retrieval (requires lios[data])
# ---------------------------------------------------------------------------


def run_pipeline(
    question: str,
    index_path: str = "data/index.faiss",
    chunks_path: str = "data/chunks.pkl",
    top_k: int = 5,
    model: str | None = None,
) -> dict[str, Any]:
    """Run the FAISS-based RAG pipeline for a legal question.

    Requires the ``lios[data]`` extras (``sentence-transformers``,
    ``faiss-cpu``).  For a pipeline that works without these extras use
    :func:`generate_answer` instead.

    Steps:
        1. Retrieve the *top_k* most relevant legal chunks from the FAISS index.
        2. Build an IRAC-structured prompt with the retrieved context.
        3. Call Ollama (Mistral) to generate an answer.
        4. Validate that the answer is grounded in the context.

    Args:
        question:    The user's legal question in English.
        index_path:  Path to the FAISS index (built by ``lios.ingestion.ingest``).
        chunks_path: Path to the pickled chunks list.
        top_k:       Number of chunks to retrieve.
        model:       Ollama model name.  Defaults to ``None``, which lets
                     :func:`~lios.llm.ollama_client.call_ollama_sync` use
                     ``OLLAMA_MODEL`` and its built-in 404-fallback logic.

    Returns:
        A dict with keys:
        - ``question``   (str)
        - ``answer``     (str)
        - ``sources``    (list[dict]) -- chunk metadata for retrieved passages
        - ``validation`` (dict)       -- ``status``, ``score``, ``reason``
    """
    from lios.llm.ollama_client import call_ollama_sync
    from lios.reasoning.legal_reasoner import build_prompt, format_context_from_chunks
    from lios.validation.validator import validate

    # 1 -- Retrieve
    chunks: list[dict[str, Any]] = []
    try:
        from lios.retrieval.retriever import retrieve

        chunks = retrieve(question, index_path=index_path, chunks_path=chunks_path, top_k=top_k)
    except (FileNotFoundError, ImportError) as exc:
        logger.warning(
            "Retrieval skipped (%s: %s). "
            "Run `python -m lios.ingestion.ingest` first or install lios[data].",
            type(exc).__name__,
            exc,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Retrieval failed unexpectedly: %s", exc)

    # 2 -- Build IRAC prompt
    context = format_context_from_chunks(chunks) if chunks else ""
    prompt = build_prompt(question, context)

    # 3 -- Call Ollama (model=None lets ollama_client use OLLAMA_MODEL + fallback)
    answer = call_ollama_sync(prompt, model=model)

    # 4 -- Validate grounding
    validation_result = validate(answer, context)
    if not validation_result.is_valid:
        logger.warning("Answer may not be grounded: %s", validation_result.reason)

    sources = [
        {
            "title": c.get("title", ""),
            "source": c.get("source", ""),
            "language": c.get("language", ""),
        }
        for c in chunks
    ]

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "validation": {
            "status": validation_result.status,
            "score": validation_result.score,
            "reason": validation_result.reason,
        },
    }


# ---------------------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------------------

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
