"""FAISS index persistence helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def save_index(index: Any, path: str | Path) -> None:
    """Persist a FAISS index to disk.

    Args:
        index: A FAISS index object.
        path:  Destination file path (e.g. ``data/index.faiss``).
    """
    try:
        import faiss  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "faiss-cpu is required for FAISS index persistence. "
            "Install it with: pip install faiss-cpu  (or pip install lios[data])"
        ) from exc

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(dest))


def load_index(path: str | Path) -> Any:
    """Load a FAISS index from disk.

    Args:
        path: Source file path.

    Returns:
        The loaded FAISS index.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ImportError: If ``faiss-cpu`` is not installed.
    """
    try:
        import faiss  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "faiss-cpu is required to load a FAISS index. "
            "Install it with: pip install faiss-cpu  (or pip install lios[data])"
        ) from exc

    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f"FAISS index not found: {src}")
    return faiss.read_index(str(src))


def build_flat_index(vectors: Any) -> Any:
    """Build a FAISS IndexFlatIP (inner-product / cosine) index from embeddings.

    Args:
        vectors: numpy.ndarray of shape (n, dim), L2-normalised.

    Raises:
        ImportError: If ``faiss-cpu`` is not installed.
    """
    try:
        import faiss  # type: ignore
        import numpy as np
    except ImportError as exc:
        raise ImportError(
            "faiss-cpu and numpy are required to build a FAISS index. "
            "Install them with: pip install faiss-cpu  (or pip install lios[data])"
        ) from exc

    vecs = np.asarray(vectors, dtype="float32")
    dim = vecs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vecs)
    return index
