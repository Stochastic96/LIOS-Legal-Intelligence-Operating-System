"""Tests for text preprocessing and metrics."""

from __future__ import annotations

import pytest

from lios.knowledge_base.ingestion.preprocessor import TextPreprocessor
from lios.knowledge_base.ingestion.document_parser import DocumentParser
from training.evaluation.metrics import rouge_n, rouge_l, citation_precision, compute_metrics


class TestTextPreprocessor:
    def setup_method(self):
        self.preprocessor = TextPreprocessor(chunk_size=200, overlap=50)

    def test_clean_removes_extra_whitespace(self) -> None:
        text = "  This  has   extra   spaces  \n\n and newlines  "
        cleaned = self.preprocessor.clean(text)
        assert "  " not in cleaned
        assert cleaned == cleaned.strip()

    def test_chunk_produces_correct_number_of_chunks(self) -> None:
        text = "A" * 1000
        chunks = self.preprocessor.chunk("reg-1", text)
        # With chunk_size=200, overlap=50, stride=150: ceil(1000/150) chunks
        assert len(chunks) >= 6

    def test_chunk_ids_are_unique(self) -> None:
        text = "Word " * 500
        chunks = self.preprocessor.chunk("reg-2", text)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_article_ref_detected_in_chunk(self) -> None:
        text = "Some preamble. Article 3 defines the scope. Some further text here."
        chunks = self.preprocessor.chunk("reg-3", text)
        refs = [c.article_ref for c in chunks if c.article_ref]
        assert len(refs) >= 1
        assert any("Article 3" in ref or "3" in ref for ref in refs)

    def test_char_ranges_are_contiguous(self) -> None:
        text = "B" * 600
        chunks = self.preprocessor.chunk("reg-4", text)
        assert chunks[0].char_start == 0
        # Each chunk's end >= previous start (they overlap)
        for i in range(1, len(chunks)):
            assert chunks[i].char_start < chunks[i - 1].char_end


class TestDocumentParser:
    def setup_method(self):
        self.parser = DocumentParser()

    def test_parse_raw_string(self) -> None:
        text = "This is a\nmultiline string."
        result = self.parser.parse(text)
        assert "multiline" in result

    def test_parse_html_strips_tags(self, tmp_path) -> None:
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><body><p>CSRD applies.</p><script>var x=1;</script></body></html>"
        )
        result = self.parser.parse(html_file)
        assert "CSRD applies." in result
        assert "var x" not in result

    def test_parse_txt_file(self, tmp_path) -> None:
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Article 1. This regulation applies.")
        result = self.parser.parse(txt_file)
        assert "Article 1" in result

    def test_parse_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.parser.parse("/nonexistent/path/file.txt")


class TestMetrics:
    def test_rouge1_identical_text(self) -> None:
        score = rouge_n("The company must report.", "The company must report.", n=1)
        assert score == 1.0

    def test_rouge1_empty_reference(self) -> None:
        score = rouge_n("some predicted text", "", n=1)
        assert score == 0.0

    def test_rouge_l_identical(self) -> None:
        score = rouge_l("abc def ghi", "abc def ghi")
        assert score == 1.0

    def test_citation_precision_perfect(self) -> None:
        score = citation_precision(["CSRD Art. 3", "SFDR Art. 4"], ["CSRD Art. 3", "SFDR Art. 4"])
        assert score == 1.0

    def test_citation_precision_partial(self) -> None:
        score = citation_precision(["CSRD Art. 3", "SFDR Art. 4"], ["CSRD Art. 3"])
        assert score == 0.5

    def test_citation_precision_empty_predicted(self) -> None:
        score = citation_precision([], ["CSRD Art. 3"])
        assert score == 0.0

    def test_compute_metrics_returns_all_keys(self) -> None:
        metrics = compute_metrics("predicted answer text", "reference answer text")
        assert "rouge1" in metrics
        assert "rouge2" in metrics
        assert "rougeL" in metrics
        assert "citation_precision" in metrics
