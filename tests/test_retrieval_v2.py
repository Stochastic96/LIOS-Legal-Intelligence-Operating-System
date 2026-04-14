"""Tests for V2 hybrid retrieval and provenance-aware citation selection."""

from __future__ import annotations

from lios.features.citation_engine import CitationEngine
from lios.retrieval.hybrid_retriever import HybridRetriever


def test_hybrid_retriever_finds_csrd_chunk() -> None:
    retriever = HybridRetriever("data/corpus/legal_chunks.jsonl")
    rows = retriever.search("what is csrd", regulations=["CSRD"], top_k=5)
    assert rows
    assert rows[0].chunk["regulation"] == "CSRD"


def test_citation_engine_prefers_provenance_corpus() -> None:
    engine = CitationEngine()
    citations = engine.get_citations("what is csrd")
    assert citations
    assert citations[0].url.startswith("https://")
