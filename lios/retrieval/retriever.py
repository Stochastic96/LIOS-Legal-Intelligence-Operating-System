"""Simple dense retriever: embed query → FAISS similarity search → top-k chunks."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

from lios.retrieval.embedder import embed_query
from lios.retrieval.vector_store import load_index

_DEFAULT_INDEX = Path("data/index.faiss")
_DEFAULT_CHUNKS = Path("data/chunks.pkl")


def retrieve(
    query: str,
    index_path: str | Path = _DEFAULT_INDEX,
    chunks_path: str | Path = _DEFAULT_CHUNKS,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve the top-*k* legal chunks most relevant to *query*.

    Embeds the query with the sentence-transformer model, performs an
    inner-product (cosine) search against the FAISS index, and returns the
    corresponding chunk metadata dicts.

    Args:
        query:       The user question (English or German).
        index_path:  Path to the FAISS index file.
        chunks_path: Path to the pickled chunks list.
        top_k:       Number of chunks to return.

    Returns:
        List of chunk dicts ordered by relevance (most relevant first).
        Each dict contains at least ``title``, ``text``, and ``source``.

    Raises:
        FileNotFoundError: If the index or chunks file does not exist.
    """
    import numpy as np

    index = load_index(index_path)

    chunks_file = Path(chunks_path)
    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_file}")
    with chunks_file.open("rb") as fh:
        chunks: list[dict[str, Any]] = pickle.load(fh)

    q_vec = embed_query(query)
    q_arr = np.asarray([q_vec], dtype="float32")

    n_results = min(top_k, index.ntotal)
    _scores, indices = index.search(q_arr, n_results)

    results: list[dict[str, Any]] = []
    for idx in indices[0]:
        if 0 <= idx < len(chunks):
            results.append(chunks[idx])
    return results
