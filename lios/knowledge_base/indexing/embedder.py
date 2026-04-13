"""Local text embedder using sentence-transformers."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from lios.config import settings
from lios.utils.logger import get_logger

logger = get_logger(__name__)


class Embedder:
    """
    Wraps a sentence-transformers model to produce dense vector embeddings.
    The model is loaded lazily on first use (avoid import-time GPU allocation).
    """

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.embedding_model
        self._model = None  # lazy-loaded

    @property
    def model(self):
        if self._model is None:
            logger.info("Loading embedding model: %s", self._model_name)
            from sentence_transformers import SentenceTransformer  # lazy

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return a 2-D float32 array of shape (n_texts, embedding_dim)."""
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.astype(np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        """Return a 1-D float32 array for a single text."""
        return self.embed([text])[0]

    @property
    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()
