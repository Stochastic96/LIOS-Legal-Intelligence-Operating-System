"""Offline unit tests for lios/ingestion/pdf_ingester.py.

All tests use in-memory mocks — no real PDFs are required.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from lios.ingestion.pdf_ingester import (
    _infer_regulation,
    _load_existing_prefixes,
    _split_by_articles,
    _split_by_tokens,
    extract_chunks_from_pdf,
    ingest_pdfs,
)

# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------

_ARTICLE_TEXT = (
    "Article 1 Subject matter and scope\n"
    "This regulation establishes sustainability reporting requirements.\n"
    "All large undertakings shall comply with these rules.\n"
    "Article 2 Definitions\n"
    "For the purposes of this Regulation: 'large undertaking' means a company "
    "exceeding two of three size criteria as defined herein.\n"
    "Article 3 Scope of application\n"
    "Member States shall require undertakings to include in their management "
    "report information on sustainability matters.\n"
)

_SHORT_TEXT = "This text has no article markers whatsoever just plain content repeated. " * 30


# ---------------------------------------------------------------------------
# Tests for _infer_regulation
# ---------------------------------------------------------------------------


class TestInferRegulation:
    def test_csrd(self) -> None:
        assert _infer_regulation("csrd_directive") == "CSRD"

    def test_esrs(self) -> None:
        assert _infer_regulation("esrs_standards_2023") == "ESRS"

    def test_taxonomy(self) -> None:
        assert _infer_regulation("eu_taxonomy_regulation") == "EU_TAXONOMY"

    def test_sfdr(self) -> None:
        assert _infer_regulation("sfdr_delegated") == "SFDR"

    def test_gdpr(self) -> None:
        assert _infer_regulation("gdpr_full_text") == "GDPR"

    def test_lksg(self) -> None:
        assert _infer_regulation("lksg_2023") == "LkSG"

    def test_unknown_uses_stem(self) -> None:
        assert _infer_regulation("custom_law_document") == "custom_law_document"

    def test_case_insensitive(self) -> None:
        assert _infer_regulation("CSRD_Directive") == "CSRD"


# ---------------------------------------------------------------------------
# Tests for _split_by_articles
# ---------------------------------------------------------------------------


class TestSplitByArticles:
    def test_finds_articles(self) -> None:
        chunks = _split_by_articles(_ARTICLE_TEXT, "CSRD", "test.pdf")
        assert len(chunks) >= 2

    def test_article_ids(self) -> None:
        chunks = _split_by_articles(_ARTICLE_TEXT, "CSRD", "test.pdf")
        articles = {c["article"] for c in chunks}
        assert "Art.1" in articles
        assert "Art.2" in articles

    def test_chunk_type_is_article(self) -> None:
        chunks = _split_by_articles(_ARTICLE_TEXT, "CSRD", "test.pdf")
        for c in chunks:
            assert c["chunk_type"] == "article"

    def test_chunk_fields(self) -> None:
        chunks = _split_by_articles(_ARTICLE_TEXT, "CSRD", "test.pdf")
        required = {"text", "regulation", "article", "celex_id", "source", "filename", "jurisdiction", "chunk_type"}
        for c in chunks:
            assert required.issubset(c.keys())

    def test_regulation_field(self) -> None:
        chunks = _split_by_articles(_ARTICLE_TEXT, "CSRD", "csrd.pdf")
        for c in chunks:
            assert c["regulation"] == "CSRD"

    def test_source_is_pdf(self) -> None:
        chunks = _split_by_articles(_ARTICLE_TEXT, "CSRD", "test.pdf")
        for c in chunks:
            assert c["source"] == "pdf"

    def test_jurisdiction_is_eu(self) -> None:
        chunks = _split_by_articles(_ARTICLE_TEXT, "CSRD", "test.pdf")
        for c in chunks:
            assert c["jurisdiction"] == "EU"

    def test_celex_id_empty(self) -> None:
        chunks = _split_by_articles(_ARTICLE_TEXT, "CSRD", "test.pdf")
        for c in chunks:
            assert c["celex_id"] == ""

    def test_returns_empty_for_no_articles(self) -> None:
        chunks = _split_by_articles("No articles here at all.", "CSRD", "test.pdf")
        assert chunks == []


# ---------------------------------------------------------------------------
# Tests for _split_by_tokens
# ---------------------------------------------------------------------------


class TestSplitByTokens:
    def test_produces_chunks(self) -> None:
        chunks = _split_by_tokens(_SHORT_TEXT, "CSRD", "test.pdf")
        assert len(chunks) >= 1

    def test_chunk_type_is_chunk(self) -> None:
        chunks = _split_by_tokens(_SHORT_TEXT, "CSRD", "test.pdf")
        for c in chunks:
            assert c["chunk_type"] == "chunk"

    def test_chunk_size_bounded(self) -> None:
        # Each chunk should have at most ~500 tokens (words)
        chunks = _split_by_tokens(_SHORT_TEXT, "CSRD", "test.pdf")
        for c in chunks:
            word_count = len(c["text"].split())
            assert word_count <= 550  # allow slight overage from join

    def test_overlap_produces_multiple_chunks_for_long_text(self) -> None:
        long_text = "word " * 1200
        chunks = _split_by_tokens(long_text, "CSRD", "test.pdf")
        assert len(chunks) >= 2


# ---------------------------------------------------------------------------
# Tests for extract_chunks_from_pdf
# ---------------------------------------------------------------------------


class TestExtractChunksFromPdf:
    def _make_mock_pdf(self, text: str):
        """Return a mock pypdf module whose PdfReader yields *text* on page 0."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = text
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pypdf = MagicMock()
        mock_pypdf.PdfReader.return_value = mock_reader
        return mock_pypdf

    def test_article_split_used_when_markers_present(self, tmp_path: Path) -> None:
        pdf_file = tmp_path / "csrd_directive.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        mock_pypdf = self._make_mock_pdf(_ARTICLE_TEXT)
        with patch("lios.ingestion.pdf_ingester.pypdf", mock_pypdf, create=True):
            with patch("lios.ingestion.pdf_ingester._extract_full_text", return_value=_ARTICLE_TEXT):
                chunks = extract_chunks_from_pdf(pdf_file)
        assert len(chunks) >= 2
        assert all(c["chunk_type"] == "article" for c in chunks)

    def test_token_split_used_when_no_article_markers(self, tmp_path: Path) -> None:
        pdf_file = tmp_path / "custom_doc.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        with patch("lios.ingestion.pdf_ingester._extract_full_text", return_value=_SHORT_TEXT):
            chunks = extract_chunks_from_pdf(pdf_file)
        assert len(chunks) >= 1
        assert all(c["chunk_type"] == "chunk" for c in chunks)

    def test_regulation_inferred_from_filename(self, tmp_path: Path) -> None:
        pdf_file = tmp_path / "sfdr_document.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        with patch("lios.ingestion.pdf_ingester._extract_full_text", return_value=_ARTICLE_TEXT):
            chunks = extract_chunks_from_pdf(pdf_file)
        assert all(c["regulation"] == "SFDR" for c in chunks)

    def test_empty_text_returns_no_chunks(self, tmp_path: Path) -> None:
        pdf_file = tmp_path / "empty.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        with patch("lios.ingestion.pdf_ingester._extract_full_text", return_value="   "):
            chunks = extract_chunks_from_pdf(pdf_file)
        assert chunks == []


# ---------------------------------------------------------------------------
# Tests for _load_existing_prefixes
# ---------------------------------------------------------------------------


class TestLoadExistingPrefixes:
    def test_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        prefixes = _load_existing_prefixes(tmp_path / "nonexistent.jsonl")
        assert prefixes == set()

    def test_returns_first_80_chars(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        text = "A" * 100
        corpus.write_text(json.dumps({"text": text}) + "\n")
        prefixes = _load_existing_prefixes(corpus)
        assert text[:80] in prefixes

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        corpus.write_text("not json\n" + json.dumps({"text": "hello world"}) + "\n")
        prefixes = _load_existing_prefixes(corpus)
        assert "hello world" in prefixes


# ---------------------------------------------------------------------------
# Tests for ingest_pdfs
# ---------------------------------------------------------------------------


class TestIngestPdfs:
    def test_missing_folder_returns_zero(self, tmp_path: Path) -> None:
        result = ingest_pdfs(folder=tmp_path / "nonexistent", corpus_path=tmp_path / "out.jsonl")
        assert result == 0

    def test_empty_folder_returns_zero(self, tmp_path: Path) -> None:
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        result = ingest_pdfs(folder=pdf_dir, corpus_path=tmp_path / "out.jsonl")
        assert result == 0

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "csrd_directive.pdf").write_bytes(b"%PDF fake")
        corpus = tmp_path / "corpus.jsonl"

        with patch("lios.ingestion.pdf_ingester._extract_full_text", return_value=_ARTICLE_TEXT):
            ingest_pdfs(folder=pdf_dir, corpus_path=corpus, dry_run=True)

        assert not corpus.exists()

    def test_writes_chunks_to_jsonl(self, tmp_path: Path) -> None:
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "csrd_directive.pdf").write_bytes(b"%PDF fake")
        corpus = tmp_path / "corpus.jsonl"

        with patch("lios.ingestion.pdf_ingester._extract_full_text", return_value=_ARTICLE_TEXT):
            with patch("lios.retrieval.chroma_retriever.ingest_jsonl", return_value=0):
                count = ingest_pdfs(folder=pdf_dir, corpus_path=corpus)

        assert count > 0
        lines = [l for l in corpus.read_text().splitlines() if l.strip()]
        assert len(lines) == count

    def test_deduplication_prevents_double_write(self, tmp_path: Path) -> None:
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "csrd_directive.pdf").write_bytes(b"%PDF fake")
        corpus = tmp_path / "corpus.jsonl"

        with patch("lios.ingestion.pdf_ingester._extract_full_text", return_value=_ARTICLE_TEXT):
            with patch("lios.retrieval.chroma_retriever.ingest_jsonl", return_value=0):
                first_count = ingest_pdfs(folder=pdf_dir, corpus_path=corpus)
                second_count = ingest_pdfs(folder=pdf_dir, corpus_path=corpus)

        assert first_count > 0
        assert second_count == 0

    def test_chunk_fields_written_to_jsonl(self, tmp_path: Path) -> None:
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "csrd_directive.pdf").write_bytes(b"%PDF fake")
        corpus = tmp_path / "corpus.jsonl"

        with patch("lios.ingestion.pdf_ingester._extract_full_text", return_value=_ARTICLE_TEXT):
            with patch("lios.retrieval.chroma_retriever.ingest_jsonl", return_value=0):
                ingest_pdfs(folder=pdf_dir, corpus_path=corpus)

        chunks = [json.loads(l) for l in corpus.read_text().splitlines() if l.strip()]
        assert chunks
        required = {"text", "regulation", "article", "celex_id", "source", "filename", "jurisdiction", "chunk_type"}
        for chunk in chunks:
            assert required.issubset(chunk.keys())
            assert chunk["source"] == "pdf"
            assert chunk["regulation"] == "CSRD"
