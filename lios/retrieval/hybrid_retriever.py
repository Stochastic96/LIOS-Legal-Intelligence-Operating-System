"""Three-stage hybrid legal retrieval (BM25 + semantic + grounded rerank)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    """Hybrid retriever with graceful fallbacks when optional deps are unavailable."""

    def __init__(self, corpus_path: str | Path = "data/corpus/legal_chunks.jsonl") -> None:
        self.corpus_path = Path(corpus_path)
        self._chunks: list[dict[str, Any]] = self._load_chunks()
        self._tokenized_docs = [
            self._tokenize(f"{c.get('regulation', '')} {c.get('title', '')} {c.get('text', '')}")
            for c in self._chunks
        ]
        self._bm25 = self._build_bm25_index(self._tokenized_docs)

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

    def _stage_b_semantic(self, query: str) -> list[float]:
        # Optional dense retrieval; fallback returns zeros.
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
        except Exception:
            return [0.0 for _ in self._chunks]

        if not self._chunks:
            return []

        model = SentenceTransformer("all-MiniLM-L6-v2")
        docs = [f"{c.get('title', '')} {c.get('text', '')}" for c in self._chunks]
        doc_vecs = model.encode(docs, normalize_embeddings=True)
        q_vec = model.encode([query], normalize_embeddings=True)[0]

        scores = (doc_vecs @ q_vec).tolist()
        # Shift from [-1,1] toward [0,1]
        return [max(0.0, (s + 1.0) / 2.0) for s in scores]

    def _stage_c_grounded(self, chunk: dict[str, Any]) -> float:
        has_source = bool(chunk.get("source_url"))
        has_article = bool(chunk.get("article"))
        has_doc = bool(chunk.get("celex_or_doc_id"))
        fields = [has_source, has_article, has_doc]
        return sum(1.0 for ok in fields if ok) / len(fields)
