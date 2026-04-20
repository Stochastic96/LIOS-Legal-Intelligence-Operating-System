"""Three-stage hybrid legal retrieval (BM25 + semantic + grounded rerank)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level SentenceTransformer singleton – loaded once, reused always.
# This avoids the 1-3 second model-load penalty on every search call.
# ---------------------------------------------------------------------------
_SENTENCE_MODEL_NAME = "all-MiniLM-L6-v2"
_sentence_model: Any = None  # SentenceTransformer | None


def _get_sentence_model() -> Any:
    """Return the shared SentenceTransformer, loading it the first time."""
    global _sentence_model
    if _sentence_model is not None:
        return _sentence_model
    try:
        from sentence_transformers import SentenceTransformer

        _sentence_model = SentenceTransformer(_SENTENCE_MODEL_NAME)
        logger.info("SentenceTransformer '%s' loaded.", _SENTENCE_MODEL_NAME)
    except Exception as exc:
        logger.warning("sentence-transformers unavailable: %s", exc)
        _sentence_model = None
    return _sentence_model


@dataclass
class RetrievedChunk:
    chunk: dict[str, Any]
    score_lexical: float
    score_semantic: float
    score_grounded: float

    @property
    def total_score(self) -> float:
        return self.score_lexical * 0.55 + self.score_semantic * 0.30 + self.score_grounded * 0.15


class HybridRetriever:
    """Hybrid retriever with graceful fallbacks when optional deps are unavailable.

    Improvements over the original:
    * SentenceTransformer is a module-level singleton – loaded once per process.
    * Document embeddings are computed once at construction time, not per query.
    * FAISS index (if available) and embeddings are persisted to disk so they
      survive application restarts without full re-encoding.
    """

    _EMBED_CACHE_SUFFIX = ".embeddings.npy"
    _FAISS_CACHE_SUFFIX = ".faiss"

    def __init__(self, corpus_path: str | Path = "data/corpus/legal_chunks.jsonl") -> None:
        self.corpus_path = Path(corpus_path)
        self._chunks: list[dict[str, Any]] = self._load_chunks()
        self._tokenized_docs = [
            self._tokenize(f"{c.get('regulation', '')} {c.get('title', '')} {c.get('text', '')}")
            for c in self._chunks
        ]
        self._bm25 = self._build_bm25_index(self._tokenized_docs)
        # Pre-compute semantic embeddings once at startup.
        self._doc_vecs: Any = self._load_or_build_doc_vecs()
        # Optionally build a FAISS index for fast ANN search.
        self._faiss_index: Any = self._load_or_build_faiss_index(self._doc_vecs)

    # ------------------------------------------------------------------
    # Chunk loading
    # ------------------------------------------------------------------

    def _load_chunks(self) -> list[dict[str, Any]]:
        if not self.corpus_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.corpus_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    # ------------------------------------------------------------------
    # BM25 lexical index
    # ------------------------------------------------------------------

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", text.lower())

    def _build_bm25_index(self, tokenized_docs: list[list[str]]) -> Any | None:
        try:
            from rank_bm25 import BM25Okapi
        except Exception:
            return None
        if not tokenized_docs:
            return None
        return BM25Okapi(tokenized_docs)

    # ------------------------------------------------------------------
    # Semantic embeddings – built once, persisted to disk
    # ------------------------------------------------------------------

    def _embed_cache_path(self) -> Path:
        return self.corpus_path.with_suffix(self._EMBED_CACHE_SUFFIX)

    def _faiss_cache_path(self) -> Path:
        return self.corpus_path.with_suffix(self._FAISS_CACHE_SUFFIX)

    def _load_or_build_doc_vecs(self) -> Any:
        """Return numpy doc-embedding matrix, loading from cache if available."""
        if not self._chunks:
            return None

        model = _get_sentence_model()
        if model is None:
            return None

        try:
            import numpy as np
        except ImportError:
            return None

        cache = self._embed_cache_path()
        if cache.exists():
            try:
                vecs = np.load(str(cache))
                if vecs.shape[0] == len(self._chunks):
                    logger.debug("Loaded %d doc embeddings from cache %s.", vecs.shape[0], cache)
                    return vecs
                logger.debug("Embedding cache size mismatch; rebuilding.")
            except Exception as exc:
                logger.warning("Failed to load embedding cache: %s", exc)

        logger.info("Computing doc embeddings for %d chunks (this may take a moment)…", len(self._chunks))
        docs = [f"{c.get('title', '')} {c.get('text', '')}" for c in self._chunks]
        vecs = model.encode(docs, normalize_embeddings=True, show_progress_bar=False)

        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.save(str(cache), vecs)
            logger.debug("Saved embedding cache to %s.", cache)
        except Exception as exc:
            logger.warning("Could not save embedding cache: %s", exc)

        return vecs

    def _load_or_build_faiss_index(self, doc_vecs: Any) -> Any:
        """Build (or reload) a FAISS flat-IP index for fast ANN search."""
        if doc_vecs is None:
            return None
        try:
            import faiss  # type: ignore
            import numpy as np
        except ImportError:
            return None

        cache = self._faiss_cache_path()
        dim = doc_vecs.shape[1]

        if cache.exists():
            try:
                idx = faiss.read_index(str(cache))
                if idx.ntotal == len(self._chunks):
                    logger.debug("Loaded FAISS index (%d vectors) from %s.", idx.ntotal, cache)
                    return idx
                logger.debug("FAISS index size mismatch; rebuilding.")
            except Exception as exc:
                logger.warning("Failed to load FAISS index: %s", exc)

        idx = faiss.IndexFlatIP(dim)
        idx.add(np.asarray(doc_vecs, dtype="float32"))
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(idx, str(cache))
            logger.debug("Saved FAISS index to %s.", cache)
        except Exception as exc:
            logger.warning("Could not save FAISS index: %s", exc)

        return idx

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, regulations: list[str] | None = None, top_k: int = 8) -> list[RetrievedChunk]:
        if not self._chunks:
            return []

        q_tokens = self._tokenize(query)
        lexical_scores = self._stage_a_lexical(q_tokens)
        semantic_scores = self._stage_b_semantic(query)

        rows: list[RetrievedChunk] = []
        for i, chunk in enumerate(self._chunks):
            if regulations and chunk.get("regulation") not in regulations:
                continue

            lex = lexical_scores[i] if i < len(lexical_scores) else 0.0
            sem = semantic_scores[i] if i < len(semantic_scores) else 0.0
            grd = self._stage_c_grounded(chunk)

            if lex <= 0 and sem <= 0:
                continue

            rows.append(
                RetrievedChunk(
                    chunk=chunk,
                    score_lexical=float(lex),
                    score_semantic=float(sem),
                    score_grounded=float(grd),
                )
            )

        rows.sort(key=lambda r: r.total_score, reverse=True)
        return rows[:top_k]

    # ------------------------------------------------------------------
    # Stage A – lexical (BM25 or overlap fallback)
    # ------------------------------------------------------------------

    def _stage_a_lexical(self, q_tokens: list[str]) -> list[float]:
        if not self._chunks:
            return []
        if self._bm25 is not None:
            return list(self._bm25.get_scores(q_tokens))

        # Fallback lexical score: overlap ratio
        scores: list[float] = []
        q_set = set(q_tokens)
        for doc in self._tokenized_docs:
            if not doc:
                scores.append(0.0)
                continue
            overlap = len(q_set.intersection(set(doc)))
            scores.append(overlap / max(1, len(q_set)))
        return scores

    # ------------------------------------------------------------------
    # Stage B – semantic (pre-computed doc vecs; FAISS-accelerated if available)
    # ------------------------------------------------------------------

    def _stage_b_semantic(self, query: str) -> list[float]:
        """Compute query-doc cosine similarities using cached doc embeddings."""
        if self._doc_vecs is None or not self._chunks:
            return [0.0 for _ in self._chunks]

        model = _get_sentence_model()
        if model is None:
            return [0.0 for _ in self._chunks]

        try:
            import numpy as np
        except ImportError:
            return [0.0 for _ in self._chunks]

        q_vec = model.encode([query], normalize_embeddings=True)[0]

        if self._faiss_index is not None:
            try:
                import faiss  # noqa: F401

                scores_arr, indices = self._faiss_index.search(
                    np.asarray([q_vec], dtype="float32"), len(self._chunks)
                )
                scores_flat = [0.0] * len(self._chunks)
                for rank, idx in enumerate(indices[0]):
                    if 0 <= idx < len(self._chunks):
                        scores_flat[idx] = max(0.0, (float(scores_arr[0][rank]) + 1.0) / 2.0)
                return scores_flat
            except Exception:
                pass  # fall through to numpy path

        scores = (self._doc_vecs @ q_vec).tolist()
        return [max(0.0, (s + 1.0) / 2.0) for s in scores]

    # ------------------------------------------------------------------
    # Stage C – grounded rerank
    # ------------------------------------------------------------------

    def _stage_c_grounded(self, chunk: dict[str, Any]) -> float:
        has_source = bool(chunk.get("source_url"))
        has_article = bool(chunk.get("article"))
        has_doc = bool(chunk.get("celex_or_doc_id"))
        fields = [has_source, has_article, has_doc]
        return sum(1.0 for ok in fields if ok) / len(fields)

    # ------------------------------------------------------------------
    # Context formatting
    # ------------------------------------------------------------------

    def format_context(self, chunks: list[RetrievedChunk], max_chars: int = 4000) -> str:
        """Format retrieved chunks into a single context string for an LLM prompt.

        Args:
            chunks:    Ranked list of retrieved chunks.
            max_chars: Soft character limit; stops adding chunks once exceeded.

        Returns:
            A newline-delimited string of labelled excerpts.
        """
        parts: list[str] = []
        total = 0
        for i, rc in enumerate(chunks, start=1):
            chunk = rc.chunk
            regulation = chunk.get("regulation", "")
            article = chunk.get("article", "")
            title = chunk.get("title", "")
            text = chunk.get("text", "").strip()
            header = f"[{i}] {regulation}"
            if article:
                header += f" {article}"
            if title:
                header += f" – {title}"
            entry = f"{header}\n{text}"
            if total + len(entry) > max_chars and parts:
                break
            parts.append(entry)
            total += len(entry)
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

import threading as _threading

_retriever_singleton: HybridRetriever | None = None
_retriever_lock = _threading.Lock()


def get_retriever() -> HybridRetriever:
    """Return the shared HybridRetriever singleton, creating it on first call.

    Thread-safe: uses a lock to prevent duplicate initialisation under concurrent
    requests at startup.
    """
    global _retriever_singleton
    if _retriever_singleton is None:
        with _retriever_lock:
            if _retriever_singleton is None:
                _retriever_singleton = HybridRetriever()
    return _retriever_singleton

