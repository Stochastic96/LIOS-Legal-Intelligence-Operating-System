"""LIOS entry point – exposes FastAPI app, Click CLI, and standalone RAG pipeline.

Standalone pipeline (no API server required)::

    from lios.main import run_pipeline
    result = run_pipeline("What rights does GDPR give to data subjects?")
    print(result["answer"])

Full flow:
    User question
    → retrieve()          (FAISS dense retrieval)
    → build_prompt()      (IRAC legal reasoning prompt)
    → call Ollama/Mistral (LLM generation)
    → validate()          (grounding check)
    → return answer + sources
"""

from __future__ import annotations

import logging
from typing import Any

from lios.api.routes import app
from lios.cli.interface import cli

logger = logging.getLogger(__name__)

MODEL = "mistral"

__all__ = ["app", "cli", "run_pipeline", "MODEL"]


def run_pipeline(
    question: str,
    index_path: str = "data/index.faiss",
    chunks_path: str = "data/chunks.pkl",
    top_k: int = 5,
    model: str = MODEL,
) -> dict[str, Any]:
    """Run the full RAG pipeline for a legal question.

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
        model:       Ollama model name to use.

    Returns:
        A dict with keys:
        - ``question`` (str)
        - ``answer``   (str)
        - ``sources``  (list[dict])  – chunk metadata for the retrieved passages
        - ``validation`` (dict)      – ``status``, ``score``, ``reason``
    """
    from lios.llm.ollama_client import call_ollama_sync
    from lios.reasoning.legal_reasoner import build_prompt, format_context_from_chunks
    from lios.retrieval.retriever import retrieve
    from lios.validation.validator import validate

    # 1 – Retrieve
    try:
        chunks = retrieve(question, index_path=index_path, chunks_path=chunks_path, top_k=top_k)
    except FileNotFoundError:
        logger.warning(
            "FAISS index or chunks not found at %s / %s. "
            "Run `python -m lios.ingestion.ingest` first.",
            index_path,
            chunks_path,
        )
        chunks = []

    # 2 – Build IRAC prompt
    context = format_context_from_chunks(chunks) if chunks else ""
    prompt = build_prompt(question, context)

    # 3 – Call Ollama
    answer = call_ollama_sync(prompt, model=model)

    # 4 – Validate grounding
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
