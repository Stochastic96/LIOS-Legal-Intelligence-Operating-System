"""Offline tests for the EUR-Lex ingestion pipeline.

All HTTP calls are mocked; no real network access is required.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest

from lios.ingestion.eurlex_fetcher import (
    REGULATIONS,
    fetch_regulation,
    fetch_regulation_from_html,
)
from lios.ingestion.legal_chunker import chunk_articles, _split_text
from lios.ingestion.models import LegalChunk

# ---------------------------------------------------------------------------
# Shared test HTML fixtures
# ---------------------------------------------------------------------------

# Modern EUR-Lex format: eli-subdivision divs
_ELI_HTML = dedent("""
    <html><body>
    <div class="eli-subdivision" id="art_1">
      <p class="ti-art">Article 1</p>
      <p class="sti-art">Subject matter and scope</p>
      <p class="norm">This Regulation establishes a framework for sustainability reporting.</p>
      <p class="norm">1. Large undertakings shall disclose information on environmental matters.</p>
    </div>
    <div class="eli-subdivision" id="art_2">
      <p class="ti-art">Article 2</p>
      <p class="sti-art">Definitions</p>
      <p class="norm">For the purposes of this Regulation the following definitions apply.</p>
      <p class="norm">'Sustainability reporting' means reporting on ESG factors.</p>
    </div>
    <div class="eli-subdivision" id="rec_1">
      <p class="ti-rec">Recital 1</p>
      <p class="norm">This is a recital and should be ignored by the article parser.</p>
    </div>
    </body></html>
""")

# Older EUR-Lex format: ti-art paragraph markers (no eli-subdivision divs)
_TI_ART_HTML = dedent("""
    <html><body>
    <p class="ti-art">Article 1</p>
    <p class="sti-art">Scope</p>
    <p class="norm">This Directive applies to large undertakings.</p>
    <p class="norm">Member States shall transpose this Directive by 2024.</p>
    <p class="ti-art">Article 2</p>
    <p class="sti-art">Definitions</p>
    <p class="norm">For the purposes of this Directive 'large undertaking' means a company exceeding two of three thresholds.</p>
    </body></html>
""")


# ---------------------------------------------------------------------------
# Tests for fetch_regulation_from_html
# ---------------------------------------------------------------------------


class TestEurLexFetcherHtmlParsing:
    def test_eli_subdivision_extracts_articles(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "csrd")
        assert len(articles) == 2, f"Expected 2 articles, got {len(articles)}"

    def test_eli_subdivision_article_ids(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "csrd")
        ids = [a["article"] for a in articles]
        assert "Art.1" in ids
        assert "Art.2" in ids

    def test_eli_subdivision_ignores_recitals(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "csrd")
        ids = [a["article"] for a in articles]
        assert not any("rec" in aid.lower() for aid in ids)

    def test_eli_subdivision_title_extraction(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "csrd")
        art1 = next(a for a in articles if a["article"] == "Art.1")
        assert "Subject matter" in art1["title"]

    def test_eli_subdivision_text_non_empty(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "csrd")
        for a in articles:
            assert len(a["text"]) > 10, f"Empty text for {a['article']}"

    def test_eli_subdivision_metadata_fields(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "csrd")
        a = articles[0]
        assert a["celex_id"] == REGULATIONS["csrd"]["celex_id"]
        assert a["regulation"] == "CSRD"
        assert a["published_date"] == REGULATIONS["csrd"]["published_date"]
        assert a["effective_date"] == REGULATIONS["csrd"]["effective_date"]

    def test_ti_art_fallback_extracts_articles(self) -> None:
        articles = fetch_regulation_from_html(_TI_ART_HTML, "csrd")
        assert len(articles) == 2

    def test_ti_art_fallback_ids(self) -> None:
        articles = fetch_regulation_from_html(_TI_ART_HTML, "csrd")
        ids = {a["article"] for a in articles}
        assert ids == {"Art.1", "Art.2"}

    def test_ti_art_subtitle_becomes_title(self) -> None:
        articles = fetch_regulation_from_html(_TI_ART_HTML, "csrd")
        art1 = next(a for a in articles if a["article"] == "Art.1")
        assert "Scope" in art1["title"]

    def test_unknown_regulation_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown regulation key"):
            fetch_regulation_from_html(_ELI_HTML, "unknown_reg")

    def test_esrs_metadata(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "esrs")
        assert articles[0]["regulation"] == "ESRS"
        assert articles[0]["celex_id"] == "32023R2772"

    def test_taxonomy_metadata(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "taxonomy")
        assert articles[0]["regulation"] == "EU_TAXONOMY"
        assert articles[0]["celex_id"] == "32020R0852"

    def test_sfdr_metadata(self) -> None:
        articles = fetch_regulation_from_html(_ELI_HTML, "sfdr")
        assert articles[0]["regulation"] == "SFDR"
        assert articles[0]["celex_id"] == "32019R2088"

    def test_empty_html_returns_empty_list(self) -> None:
        articles = fetch_regulation_from_html("<html><body></body></html>", "csrd")
        assert articles == []


# ---------------------------------------------------------------------------
# Tests for fetch_regulation (HTTP layer)
# ---------------------------------------------------------------------------


class TestFetchRegulationHTTP:
    def test_raises_for_unknown_key(self) -> None:
        with pytest.raises(ValueError, match="Unknown regulation key"):
            fetch_regulation("not_a_reg")

    def test_http_error_returns_empty_list(self) -> None:
        import httpx

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = fetch_regulation("csrd")
        assert result == []

    def test_network_error_returns_empty_list(self) -> None:
        import httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("connection refused")
            mock_client_cls.return_value = mock_client

            result = fetch_regulation("csrd")
        assert result == []

    def test_successful_fetch_parses_articles(self) -> None:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = _ELI_HTML

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            articles = fetch_regulation("csrd")
        assert len(articles) == 2


# ---------------------------------------------------------------------------
# Tests for legal_chunker
# ---------------------------------------------------------------------------


def _make_article(
    article: str = "Art.1",
    title: str = "Subject matter",
    text: str = "Default text.",
    regulation: str = "CSRD",
    celex_id: str = "32022L2464",
    published_date: str = "2022-12-16",
    effective_date: str = "2023-01-05",
) -> dict:
    return {
        "article": article,
        "title": title,
        "text": text,
        "regulation": regulation,
        "celex_id": celex_id,
        "published_date": published_date,
        "effective_date": effective_date,
    }


def _long_text(word_count: int) -> str:
    """Generate a deterministic text with *word_count* words."""
    word = "compliance"
    sentences = []
    for i in range(0, word_count, 10):
        sentences.append(" ".join([f"{word}{j}" for j in range(i, min(i + 10, word_count))]) + ".")
    return " ".join(sentences)


class TestLegalChunker:
    def test_short_article_produces_one_chunk(self) -> None:
        article = _make_article(text="Short text with only a few words.")
        chunks = chunk_articles([article])
        assert len(chunks) == 1

    def test_chunk_is_legal_chunk_instance(self) -> None:
        article = _make_article(text="Short text.")
        chunks = chunk_articles([article])
        assert isinstance(chunks[0], LegalChunk)

    def test_chunk_fields_populated(self) -> None:
        article = _make_article()
        chunks = chunk_articles([article])
        c = chunks[0]
        assert c.regulation == "CSRD"
        assert c.celex_or_doc_id == "32022L2464"
        assert c.jurisdiction == "EU"
        assert c.article == "Art.1"
        assert c.title == "Subject matter"
        assert c.source_url.startswith("https://")
        assert c.version_hash
        assert c.chunk_id

    def test_long_article_splits_into_multiple_chunks(self) -> None:
        # 600 words >> _MAX_WORDS (≈444), so it must split.
        text = _long_text(600)
        article = _make_article(text=text)
        chunks = chunk_articles([article])
        assert len(chunks) >= 2

    def test_split_chunks_have_part_suffix(self) -> None:
        text = _long_text(600)
        article = _make_article(text=text)
        chunks = chunk_articles([article])
        if len(chunks) > 1:
            assert "part" in chunks[0].title.lower()

    def test_split_chunks_have_unique_article_ids(self) -> None:
        text = _long_text(600)
        article = _make_article(text=text)
        chunks = chunk_articles([article])
        if len(chunks) > 1:
            ids = [c.article for c in chunks]
            assert len(ids) == len(set(ids))

    def test_empty_articles_list(self) -> None:
        assert chunk_articles([]) == []

    def test_multiple_articles(self) -> None:
        articles = [_make_article(article=f"Art.{i}", title=f"Art {i}") for i in range(1, 6)]
        chunks = chunk_articles(articles)
        assert len(chunks) == 5

    def test_source_url_csrd(self) -> None:
        article = _make_article(regulation="CSRD")
        chunks = chunk_articles([article])
        assert "32022L2464" in chunks[0].source_url

    def test_source_url_esrs(self) -> None:
        article = _make_article(regulation="ESRS", celex_id="32023R2772")
        chunks = chunk_articles([article])
        assert "32023R2772" in chunks[0].source_url

    def test_source_url_eu_taxonomy(self) -> None:
        article = _make_article(regulation="EU_TAXONOMY", celex_id="32020R0852")
        chunks = chunk_articles([article])
        assert "32020R0852" in chunks[0].source_url

    def test_source_url_sfdr(self) -> None:
        article = _make_article(regulation="SFDR", celex_id="32019R2088")
        chunks = chunk_articles([article])
        assert "32019R2088" in chunks[0].source_url

    def test_chunk_text_not_empty(self) -> None:
        article = _make_article(text="Some meaningful legal content for testing.")
        chunks = chunk_articles([article])
        assert all(len(c.text) > 0 for c in chunks)

    def test_version_hash_changes_with_text(self) -> None:
        a1 = _make_article(text="First version of the article text.")
        a2 = _make_article(text="Second version of the article text.")
        c1 = chunk_articles([a1])[0]
        c2 = chunk_articles([a2])[0]
        assert c1.version_hash != c2.version_hash

    def test_chunk_id_unique_per_article(self) -> None:
        articles = [
            _make_article(article="Art.1", text="Text one."),
            _make_article(article="Art.2", text="Text two."),
        ]
        chunks = chunk_articles(articles)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))


class TestSplitText:
    def test_short_text_returns_single_segment(self) -> None:
        text = "Short. Text."
        result = _split_text(text, min_words=100, max_words=200)
        assert len(result) == 1
        assert result[0] == text

    def test_very_long_single_sentence_is_force_split(self) -> None:
        # One sentence with 1000 words, max=200
        text = " ".join(["word"] * 1000)
        result = _split_text(text, min_words=150, max_words=200)
        assert len(result) > 1
        for seg in result:
            assert len(seg.split()) <= 200

    def test_no_segment_is_empty(self) -> None:
        text = _long_text(500)
        result = _split_text(text, min_words=100, max_words=150)
        assert all(seg.strip() for seg in result)

    def test_concatenation_preserves_words(self) -> None:
        text = _long_text(300)
        result = _split_text(text, min_words=50, max_words=100)
        rejoined_words = " ".join(result).split()
        original_words = text.split()
        assert len(rejoined_words) == len(original_words)


# ---------------------------------------------------------------------------
# Tests for scripts/build_corpus.py
# ---------------------------------------------------------------------------


class TestBuildCorpus:
    """Integration tests for the build_corpus CLI helper (HTTP is mocked)."""

    def _mock_fetch(self, reg_key: str) -> list[dict]:
        """Return two minimal article dicts for any regulation."""
        meta = REGULATIONS[reg_key]
        return [
            {
                "article": "Art.1",
                "title": "Test Article 1",
                "text": "This is a test article about sustainability reporting requirements.",
                "regulation": meta["regulation"],
                "celex_id": meta["celex_id"],
                "published_date": meta["published_date"],
                "effective_date": meta["effective_date"],
            },
            {
                "article": "Art.2",
                "title": "Test Article 2",
                "text": "This is a second test article about sustainability reporting definitions.",
                "regulation": meta["regulation"],
                "celex_id": meta["celex_id"],
                "published_date": meta["published_date"],
                "effective_date": meta["effective_date"],
            },
        ]

    def test_build_corpus_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import build_corpus

        with patch("scripts.build_corpus.fetch_regulation", side_effect=self._mock_fetch):
            added, skipped = build_corpus(["csrd"], out)

        assert out.exists()
        assert added == 2
        assert skipped == 0

    def test_build_corpus_deduplication(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import build_corpus

        with patch("scripts.build_corpus.fetch_regulation", side_effect=self._mock_fetch):
            added1, skipped1 = build_corpus(["csrd"], out)
            added2, skipped2 = build_corpus(["csrd"], out)

        assert added1 == 2
        assert skipped1 == 0
        assert added2 == 0
        assert skipped2 == 2

    def test_build_corpus_jsonl_schema(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import build_corpus

        with patch("scripts.build_corpus.fetch_regulation", side_effect=self._mock_fetch):
            build_corpus(["csrd"], out)

        required_fields = {
            "chunk_id",
            "source_url",
            "celex_or_doc_id",
            "jurisdiction",
            "regulation",
            "article",
            "published_date",
            "effective_date",
            "version_hash",
            "ingestion_timestamp",
            "title",
            "text",
        }
        lines = out.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            obj = json.loads(line)
            missing = required_fields - set(obj.keys())
            assert not missing, f"Missing fields: {missing}"

    def test_build_corpus_jurisdiction_is_eu(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import build_corpus

        with patch("scripts.build_corpus.fetch_regulation", side_effect=self._mock_fetch):
            build_corpus(["esrs"], out)

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            obj = json.loads(line)
            assert obj["jurisdiction"] == "EU"

    def test_build_corpus_no_articles_warning(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import build_corpus

        with patch("scripts.build_corpus.fetch_regulation", return_value=[]):
            added, skipped = build_corpus(["csrd"], out)

        assert added == 0
        assert skipped == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.err

    def test_build_corpus_multiple_regulations(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import build_corpus

        with patch("scripts.build_corpus.fetch_regulation", side_effect=self._mock_fetch):
            added, skipped = build_corpus(["csrd", "esrs", "taxonomy", "sfdr"], out)

        # 2 articles × 4 regulations = 8 chunks
        assert added == 8
        assert skipped == 0

    def test_build_corpus_appends_not_overwrites(self, tmp_path: Path) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import build_corpus

        with patch("scripts.build_corpus.fetch_regulation", side_effect=self._mock_fetch):
            build_corpus(["csrd"], out)
            build_corpus(["esrs"], out)

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        # 2 CSRD + 2 ESRS = 4 lines
        assert len(lines) == 4

    def test_main_cli_prints_summary(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import main

        with patch("scripts.build_corpus.fetch_regulation", side_effect=self._mock_fetch):
            main(["--regulations", "csrd", "--output", str(out)])

        captured = capsys.readouterr()
        assert "chunks added" in captured.out

    def test_main_cli_default_regulations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        out = tmp_path / "corpus.jsonl"
        from scripts.build_corpus import main

        with patch("scripts.build_corpus.fetch_regulation", side_effect=self._mock_fetch):
            main(["--output", str(out)])

        captured = capsys.readouterr()
        # All four regulations should appear in the output header
        assert "CSRD" in captured.out
        assert "ESRS" in captured.out
