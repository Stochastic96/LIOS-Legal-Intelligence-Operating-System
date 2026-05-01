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

logger = logging.getLogger(__name__)

__all__ = ["app", "cli", "generate_answer", "run_pipeline"]


# ---------------------------------------------------------------------------
# Pipeline 1 -- Hybrid BM25/semantic retrieval (no optional deps required)
# ---------------------------------------------------------------------------


def generate_answer(question: str) -> str:
    """Answer a legal question using the LIOS routing pipeline.

    Routes the question through one of two paths:

    EASY PATH (DEFINITION / GENERAL, no company metrics, no article refs):
      1. Call Ollama/Mistral directly without corpus context.
      2. Retrieve top-5 chunks and verify grounding with FactVerifier.
      3. If grounded: return the LLM answer.
      4. If not grounded: re-ask with corpus context (RAG path).

    COMPLEX PATH (all other question types, or when easy-path fails):
      1. Retrieve top-5 chunks via HybridRetriever.
      2. Build IRAC prompt with corpus context.
      3. Call Ollama/Mistral and return the answer.

    Falls back to rule-based AnswerSynthesizer when Ollama is unavailable.

    Args:
        question: The user's legal question in natural language.

    Returns:
        A string answer.
    """
    from lios.intelligence.fact_verifier import FactVerifier
    from lios.intelligence.question_classifier import QuestionClassifier, is_easy_question
    from lios.llm.ollama_client import call_ollama_sync
    from lios.reasoning.legal_reasoner import build_direct_prompt, build_prompt
    from lios.retrieval.hybrid_retriever import get_retriever

    classifier = QuestionClassifier()
    qtype = classifier.classify(question)
    retriever = get_retriever()

    # --- EASY PATH: LLM-direct for definition/general questions ---
    if is_easy_question(question, qtype):
        try:
            llm_answer = call_ollama_sync(build_direct_prompt(question))
            top_chunks = retriever.search(question, top_k=5)
            raw_chunks = [rc.chunk for rc in top_chunks]
            if raw_chunks:
                result = FactVerifier().verify(llm_answer, raw_chunks)
                if result.is_grounded:
                    logger.debug(
                        "Easy-path LLM answer accepted (coverage=%.2f)",
                        result.source_coverage,
                    )
                    return llm_answer
                logger.debug(
                    "Easy-path answer not grounded (%.2f); re-asking with context.",
                    result.source_coverage,
                )
                # Re-ask with corpus context before giving up on Ollama
                try:
                    return call_ollama_sync(build_prompt(question, raw_chunks))
                except Exception:  # noqa: BLE001
                    pass
                from lios.intelligence.answer_synthesizer import AnswerSynthesizer
                return AnswerSynthesizer().synthesize(question, raw_chunks)
            logger.debug("No corpus chunks; returning easy-path LLM answer.")
            return llm_answer
        except Exception as exc:  # noqa: BLE001
            logger.warning("Easy-path failed (%s); falling back to RAG.", exc)

    # --- COMPLEX PATH: RAG retrieval + context-grounded prompt ---
    top_chunks = retriever.search(question, top_k=5)

    if not top_chunks:
        return "No relevant legal context found in the corpus."

    raw_chunks = [rc.chunk for rc in top_chunks]
    prompt = build_prompt(question, raw_chunks)

    try:
        return call_ollama_sync(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Ollama unavailable (%s); falling back to AnswerSynthesizer.", exc
        )

    from lios.intelligence.answer_synthesizer import AnswerSynthesizer
    return AnswerSynthesizer().synthesize(question, raw_chunks)


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
