"""Embedding helper using sentence-transformers (all-MiniLM-L6-v2)."""

from __future__ import annotations

from typing import Any

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: Any = None  # SentenceTransformer | None


def _get_model() -> Any:
    """Return the shared SentenceTransformer, loading it on first use."""
    global _model
    if _model is not None:
        return _model
    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> Any:
    """Encode a list of strings into L2-normalised embedding vectors.

    Args:
        texts: Input strings to encode.

    Returns:
        numpy.ndarray of shape (len(texts), embedding_dim).
    """
    model = _get_model()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def embed_query(query: str) -> Any:
    """Encode a single query string into a normalised embedding vector.

    Args:
        query: The query text.

    Returns:
        1-D numpy.ndarray of shape (embedding_dim,).
    """
    model = _get_model()
    vecs = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
    return vecs[0]
