"""Tests for the new RAG pipeline modules.

Covers:
- lios.ingestion.cleaner
- lios.ingestion.ingest  (chunk logic; embeddings are mocked)
- lios.retrieval.embedder  (mocked – model not available in CI)
- lios.retrieval.vector_store
- lios.retrieval.retriever  (embeddings mocked)
- lios.reasoning.legal_reasoner
- lios.validation.validator
- lios.main.run_pipeline (Ollama + embeddings mocked)
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest


def _make_random_vecs(n: int, dim: int = 64) -> np.ndarray:
    """Return L2-normalised random float32 vectors for mocking embeddings."""
    vecs = np.random.rand(n, dim).astype("float32")
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.maximum(norms, 1e-8)


# ---------------------------------------------------------------------------
# cleaner
# ---------------------------------------------------------------------------


class TestCleaner:
    def test_remove_html_strips_tags(self):
        from lios.ingestion.cleaner import remove_html

        assert remove_html("<p>Hello <b>world</b></p>") == " Hello  world  "

    def test_remove_html_handles_entities(self):
        from lios.ingestion.cleaner import remove_html

        result = remove_html("Price &amp; quality")
        assert "&amp;" not in result

    def test_normalize_whitespace_collapses_spaces(self):
        from lios.ingestion.cleaner import normalize_whitespace

        assert normalize_whitespace("hello   world\n\t!") == "hello world !"

    def test_clean_text_full_pipeline(self):
        from lios.ingestion.cleaner import clean_text

        result = clean_text("<p>  Hello   <br/>world  </p>")
        assert "<" not in result
        assert "Hello" in result
        assert "world" in result


# ---------------------------------------------------------------------------
# ingest – chunking logic (no model needed)
# ---------------------------------------------------------------------------


class TestIngestionChunking:
    def test_chunk_words_basic(self):
        from lios.ingestion.ingest import _chunk_words

        words = ["word"] * 500
        text = " ".join(words)
        chunks = _chunk_words(text, size=400, overlap=50)
        assert len(chunks) >= 2
        # Each chunk should be at most 400 words
        for chunk in chunks:
            assert len(chunk.split()) <= 400

    def test_chunk_words_short_text(self):
        from lios.ingestion.ingest import _chunk_words

        chunks = _chunk_words("hello world", size=400, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == "hello world"

    def test_chunk_words_empty(self):
        from lios.ingestion.ingest import _chunk_words

        assert _chunk_words("") == []

    def test_chunk_words_overlap(self):
        from lios.ingestion.ingest import _chunk_words

        text = " ".join(str(i) for i in range(100))
        chunks = _chunk_words(text, size=20, overlap=5)
        # Second chunk should share last 5 words of first chunk
        first_end = chunks[0].split()[-5:]
        second_start = chunks[1].split()[:5]
        assert first_end == second_start

    def test_run_ingestion_produces_index_and_pkl(self, tmp_path):
        from lios.ingestion.ingest import run_ingestion

        # Create a minimal JSON dataset
        dataset = [
            {
                "title": "BGB § 280",
                "text": "Verletzt der Schuldner eine Pflicht " * 50,
                "source": "https://example.com/bgb280",
                "language": "de",
            }
        ]
        input_file = tmp_path / "dataset.json"
        input_file.write_text(json.dumps(dataset), encoding="utf-8")

        index_path = tmp_path / "index.faiss"
        chunks_path = tmp_path / "chunks.pkl"

        # Mock embed_texts so no real model is needed
        def _fake_embed(texts):
            return _make_random_vecs(len(texts))

        with patch("lios.ingestion.ingest.embed_texts", side_effect=_fake_embed):
            total = run_ingestion(input_file, index_path, chunks_path)

        assert total > 0
        assert index_path.exists()
        assert chunks_path.exists()

        with chunks_path.open("rb") as fh:
            chunks = pickle.load(fh)
        assert len(chunks) == total
        assert "text" in chunks[0]
        assert "source" in chunks[0]


# ---------------------------------------------------------------------------
# vector_store
# ---------------------------------------------------------------------------


class TestVectorStore:
    def test_build_save_load_round_trip(self, tmp_path):
        import numpy as np

        from lios.retrieval.vector_store import build_flat_index, load_index, save_index

        vecs = np.random.rand(10, 64).astype("float32")
        index = build_flat_index(vecs)
        assert index.ntotal == 10

        path = tmp_path / "test.faiss"
        save_index(index, path)
        assert path.exists()

        loaded = load_index(path)
        assert loaded.ntotal == 10

    def test_load_index_raises_on_missing_file(self, tmp_path):
        from lios.retrieval.vector_store import load_index

        with pytest.raises(FileNotFoundError):
            load_index(tmp_path / "nonexistent.faiss")


# ---------------------------------------------------------------------------
# retriever
# ---------------------------------------------------------------------------


class TestRetriever:
    def test_retrieve_returns_chunks(self, tmp_path):
        from lios.retrieval.retriever import retrieve
        from lios.retrieval.vector_store import build_flat_index, save_index

        chunks = [
            {"title": "BGB § 280", "text": "Breach of duty damages", "source": "url1", "language": "de"},
            {"title": "GDPR Art 17", "text": "Right to erasure forgotten", "source": "url2", "language": "en"},
        ]

        vecs = _make_random_vecs(len(chunks))
        index_path = tmp_path / "index.faiss"
        chunks_path = tmp_path / "chunks.pkl"

        index = build_flat_index(vecs)
        save_index(index, index_path)

        with chunks_path.open("wb") as fh:
            pickle.dump(chunks, fh)

        # Mock embed_query to return a compatible random vector
        def _fake_embed_query(query: str) -> np.ndarray:
            return _make_random_vecs(1)[0]

        with patch("lios.retrieval.retriever.embed_query", side_effect=_fake_embed_query):
            results = retrieve("breach of contract", index_path=index_path, chunks_path=chunks_path, top_k=2)

        assert len(results) <= 2
        assert isinstance(results[0], dict)
        assert "text" in results[0]

    def test_retrieve_raises_if_index_missing(self, tmp_path):
        from lios.retrieval.retriever import retrieve

        with pytest.raises(FileNotFoundError):
            retrieve("question", index_path=tmp_path / "no.faiss", chunks_path=tmp_path / "no.pkl")


# ---------------------------------------------------------------------------
# legal_reasoner
# ---------------------------------------------------------------------------


class TestLegalReasoner:
    def test_build_prompt_contains_question(self):
        from lios.reasoning.legal_reasoner import build_prompt

        prompt = build_prompt("What is breach of contract?", "§ 280 BGB relevant text")
        assert "What is breach of contract?" in prompt

    def test_build_prompt_contains_context(self):
        from lios.reasoning.legal_reasoner import build_prompt

        prompt = build_prompt("test question", "§ 280 BGB relevant text")
        assert "§ 280 BGB relevant text" in prompt

    def test_build_prompt_contains_irac_labels(self):
        from lios.reasoning.legal_reasoner import build_prompt

        prompt = build_prompt("test?", "some context")
        for label in ("Issue", "Rule", "Analysis", "Conclusion"):
            assert label in prompt

    def test_build_prompt_enforces_english_output(self):
        from lios.reasoning.legal_reasoner import build_prompt

        prompt = build_prompt("test?", "some context")
        assert "English" in prompt or "english" in prompt.lower()

    def test_build_prompt_no_hallucination_instruction(self):
        from lios.reasoning.legal_reasoner import build_prompt

        prompt = build_prompt("test?", "some context")
        assert "ONLY" in prompt or "only" in prompt.lower()

    def test_build_prompt_empty_context(self):
        from lios.reasoning.legal_reasoner import build_prompt

        prompt = build_prompt("question?", "")
        assert "No relevant context" in prompt or "not contain" in prompt

    def test_format_context_from_chunks(self):
        from lios.reasoning.legal_reasoner import format_context_from_chunks

        chunks = [
            {"title": "BGB § 280", "text": "Schuldner verletzt Pflicht", "source": "https://bgb.de"},
            {"title": "GDPR Art 17", "text": "Right to be forgotten", "source": "https://gdpr.eu"},
        ]
        ctx = format_context_from_chunks(chunks)
        assert "[1]" in ctx
        assert "[2]" in ctx
        assert "BGB § 280" in ctx
        assert "GDPR Art 17" in ctx

    def test_format_context_respects_max_chars(self):
        from lios.reasoning.legal_reasoner import format_context_from_chunks

        chunks = [{"title": f"Doc {i}", "text": "x" * 1000, "source": ""} for i in range(10)]
        ctx = format_context_from_chunks(chunks, max_chars=500)
        assert len(ctx) < 5000


# ---------------------------------------------------------------------------
# validator
# ---------------------------------------------------------------------------


class TestValidator:
    def test_valid_when_answer_overlaps_context(self):
        from lios.validation.validator import validate

        context = "The controller must erase personal data without undue delay upon request."
        answer = "Under GDPR, the controller must erase personal data without undue delay."
        result = validate(answer, context)
        assert result.status == "VALID"
        assert result.score > 0

    def test_invalid_when_answer_is_hallucinated(self):
        from lios.validation.validator import validate

        context = "GDPR Article 17 grants the right to erasure of personal data."
        answer = (
            "The Martian Constitution requires all data to be stored on Mars colonies "
            "and transmitted via quantum satellite uplink."
        )
        result = validate(answer, context)
        assert result.status == "INVALID"

    def test_valid_when_answer_declines(self):
        from lios.validation.validator import validate

        answer = "The provided legal context does not contain sufficient information."
        result = validate(answer, "some unrelated context")
        assert result.status == "VALID"

    def test_invalid_for_empty_answer(self):
        from lios.validation.validator import validate

        result = validate("", "some context")
        assert result.status == "INVALID"

    def test_result_has_score(self):
        from lios.validation.validator import validate

        result = validate("some answer with words", "some answer with words and more")
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0

    def test_is_valid_property(self):
        from lios.validation.validator import ValidationResult

        vr = ValidationResult(status="VALID", score=0.8, reason="ok")
        assert vr.is_valid is True

        vr2 = ValidationResult(status="INVALID", score=0.05, reason="low overlap")
        assert vr2.is_valid is False


# ---------------------------------------------------------------------------
# run_pipeline (end-to-end, Ollama mocked)
# ---------------------------------------------------------------------------


class TestRunPipeline:
    def test_pipeline_returns_required_keys(self, tmp_path):
        from lios.retrieval.vector_store import build_flat_index, save_index

        chunks = [
            {
                "title": "BGB § 280",
                "text": "breach of contract damages Schuldner Pflicht",
                "source": "https://example.com",
                "language": "de",
            }
        ]
        vecs = _make_random_vecs(len(chunks))
        index_path = tmp_path / "index.faiss"
        chunks_path = tmp_path / "chunks.pkl"
        save_index(build_flat_index(vecs), index_path)
        with chunks_path.open("wb") as fh:
            pickle.dump(chunks, fh)

        def _fake_embed_query(query: str) -> np.ndarray:
            return _make_random_vecs(1)[0]

        with (
            patch("lios.retrieval.retriever.embed_query", side_effect=_fake_embed_query),
            patch("lios.llm.ollama_client.call_ollama_sync", return_value="Issue\nBreach of contract.\nConclusion\nDamages apply."),
        ):
            from lios.main import run_pipeline

            result = run_pipeline(
                "What is breach of contract?",
                index_path=str(index_path),
                chunks_path=str(chunks_path),
            )

        assert "question" in result
        assert "answer" in result
        assert "sources" in result
        assert "validation" in result
        assert isinstance(result["sources"], list)
        assert result["validation"]["status"] in ("VALID", "INVALID")

    def test_pipeline_handles_missing_index_gracefully(self, tmp_path):
        with patch("lios.llm.ollama_client.call_ollama_sync", return_value="No context answer."):
            from lios.main import run_pipeline

            result = run_pipeline(
                "What is GDPR?",
                index_path=str(tmp_path / "no_index.faiss"),
                chunks_path=str(tmp_path / "no_chunks.pkl"),
            )

        assert result["answer"] == "No context answer."
        assert result["sources"] == []


# ---------------------------------------------------------------------------
# Integration: ingest → retrieve → build_prompt → validate
# ---------------------------------------------------------------------------


class TestEndToEndIngestionRetrieval:
    def test_ingest_then_retrieve(self, tmp_path):
        """Full pipeline: write JSON → ingest → retrieve → check results."""
        from lios.ingestion.ingest import run_ingestion
        from lios.reasoning.legal_reasoner import build_prompt, format_context_from_chunks
        from lios.retrieval.retriever import retrieve
        from lios.validation.validator import validate

        dataset = [
            {
                "title": "GDPR Article 17",
                "text": (
                    "The data subject shall have the right to obtain from the controller "
                    "the erasure of personal data concerning him or her without undue delay. "
                    "This is known as the right to erasure or right to be forgotten. "
                    "The controller must erase data when it is no longer necessary, "
                    "when consent is withdrawn, or when data has been unlawfully processed. "
                ) * 5,
                "source": "https://gdpr-info.eu/art-17-gdpr/",
                "language": "en",
            }
        ]
        input_file = tmp_path / "data.json"
        input_file.write_text(json.dumps(dataset), encoding="utf-8")
        index_path = tmp_path / "index.faiss"
        chunks_path = tmp_path / "chunks.pkl"

        # Track how many chunks are produced to create matching embeddings
        produced: list[int] = []

        def _fake_embed_texts(texts):
            produced.append(len(texts))
            return _make_random_vecs(len(texts))

        def _fake_embed_query(query: str) -> np.ndarray:
            return _make_random_vecs(1)[0]

        with patch("lios.ingestion.ingest.embed_texts", side_effect=_fake_embed_texts):
            total = run_ingestion(input_file, index_path, chunks_path)

        assert total > 0

        with patch("lios.retrieval.retriever.embed_query", side_effect=_fake_embed_query):
            chunks = retrieve(
                "What rights does GDPR give?",
                index_path=index_path,
                chunks_path=chunks_path,
                top_k=3,
            )

        assert len(chunks) > 0

        context = format_context_from_chunks(chunks)
        prompt = build_prompt("What rights does GDPR give?", context)
        assert "Issue" in prompt

        # Simulate a grounded answer
        grounded_answer = "Under GDPR Article 17, data subjects have the right to erasure of personal data."
        result = validate(grounded_answer, context)
        assert result.status == "VALID"
