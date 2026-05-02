"""Offline tests for the CJEU + ECHR case law fetcher.

All HTTP calls are mocked; no real network access is required.
"""

from __future__ import annotations

import json
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest

from lios.ingestion.caselaw_fetcher import (
    CJEU_CASES,
    ECHR_TOPICS,
    fetch_cjeu_cases,
    fetch_cjeu_cases_from_html,
    fetch_echr_cases,
    fetch_echr_cases_from_html,
    _make_article_dict,
)
from lios.ingestion.legal_chunker import chunk_articles

# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

_CJEU_ELI_HTML = dedent("""
    <html><body>
    <div class="eli-subdivision" id="art_1">
      <p class="ti-art">Background and facts</p>
      <p class="norm">The Data Protection Commissioner referred questions to the CJEU.</p>
      <p class="norm">Facebook Ireland Ltd transfers personal data to the United States.</p>
    </div>
    <div class="eli-subdivision" id="art_2">
      <p class="ti-art">Ruling of the Court</p>
      <p class="norm">Decision 2016/1250 is invalid as it does not ensure an adequate level of protection.</p>
      <p class="norm">Standard contractual clauses remain valid subject to supervisory authority scrutiny.</p>
    </div>
    </body></html>
""")

_CJEU_HEADING_HTML = dedent("""
    <html><body>
    <h2>JUDGMENT</h2>
    <p>The Court of Justice (Grand Chamber).</p>
    <p>In Case C-311/18 Data Protection Commissioner v Facebook Ireland Limited and Maximillian Schrems.</p>
    <h2>Background</h2>
    <p>Mr Schrems lodged a complaint with the Data Protection Commissioner.</p>
    <p>The complaint concerned the transfer of his personal data to Facebook Inc servers in the United States.</p>
    <h2>Decision</h2>
    <p>Decision 2016/1250 is invalid in light of Articles 7, 8 and 47 of the Charter.</p>
    </body></html>
""")

_CJEU_PARAGRAPH_HTML = dedent("""
    <html><body>
    <p>The Court, composed of the Grand Chamber, delivers this judgment.</p>
    <p>In Case C-131/12, the Court rules on the right to erasure of personal data.</p>
    <p>Google LLC as operator of a search engine is responsible for processing data.</p>
    <p>Data subjects have the right to request removal of links to their personal information.</p>
    </body></html>
""")

_ECHR_HTML = dedent("""
    <html><body>
    <h2>Facts</h2>
    <p>The applicant complained that the State surveillance of his communications violated Article 8.</p>
    <p>He relied on domestic court findings confirming interception of his phone calls.</p>
    <h2>Law</h2>
    <p>Article 8 requires that any interference with private life has a legal basis.</p>
    <p>The interference must be necessary in a democratic society for a legitimate aim.</p>
    </body></html>
""")

_HUDOC_SEARCH_RESPONSE = {
    "results": [
        {
            "columns": {
                "itemid": "001-123456",
                "docname": "CASE OF TEST v. GERMANY",
                "judgementdate": "2021-06-15T00:00:00.0Z",
                "respondent": "Germany",
            }
        }
    ]
}

_SCHREMS_META = {
    "celex_id": "62018CJ0311",
    "case_num": "C-311/18",
    "title": "Schrems II",
    "regulation": "GDPR",
    "published_date": "2020-07-16",
    "effective_date": "2020-07-16",
}

_ECHR_META = {
    "celex_id": "001-123456",
    "case_num": "001-123456",
    "title": "Test v Germany",
    "regulation": "GDPR",
    "published_date": "2021-06-15",
    "effective_date": "2021-06-15",
}


# ---------------------------------------------------------------------------
# fetch_cjeu_cases_from_html
# ---------------------------------------------------------------------------


class TestCjeuHtmlParsing:
    def test_eli_subdivision_extracts_sections(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_ELI_HTML, _SCHREMS_META)
        assert len(articles) == 2

    def test_eli_subdivision_has_text(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_ELI_HTML, _SCHREMS_META)
        for a in articles:
            assert len(a["text"]) >= 50

    def test_eli_subdivision_regulation_set(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_ELI_HTML, _SCHREMS_META)
        assert all(a["regulation"] == "GDPR" for a in articles)

    def test_eli_subdivision_celex_id_set(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_ELI_HTML, _SCHREMS_META)
        assert all(a["celex_id"] == "62018CJ0311" for a in articles)

    def test_heading_fallback_extracts_sections(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_HEADING_HTML, _SCHREMS_META)
        assert len(articles) >= 2

    def test_heading_fallback_skips_short_sections(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_HEADING_HTML, _SCHREMS_META)
        for a in articles:
            assert len(a["text"]) >= 80

    def test_paragraph_batch_fallback(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_PARAGRAPH_HTML, _SCHREMS_META)
        assert len(articles) >= 1
        assert all(a["text"] for a in articles)

    def test_source_url_uses_eurlex(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_ELI_HTML, _SCHREMS_META)
        for a in articles:
            assert "eur-lex.europa.eu" in a["source_url"]

    def test_article_id_is_slugified_title(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_ELI_HTML, _SCHREMS_META)
        for a in articles:
            assert " " not in a["article"]


# ---------------------------------------------------------------------------
# fetch_echr_cases_from_html
# ---------------------------------------------------------------------------


class TestEchrHtmlParsing:
    def test_extracts_sections_from_html(self) -> None:
        articles = fetch_echr_cases_from_html(_ECHR_HTML, _ECHR_META)
        assert len(articles) >= 2

    def test_regulation_set(self) -> None:
        articles = fetch_echr_cases_from_html(_ECHR_HTML, _ECHR_META)
        assert all(a["regulation"] == "GDPR" for a in articles)

    def test_source_url_uses_hudoc(self) -> None:
        articles = fetch_echr_cases_from_html(_ECHR_HTML, _ECHR_META)
        for a in articles:
            assert "hudoc.echr.coe.int" in a["source_url"]


# ---------------------------------------------------------------------------
# _make_article_dict
# ---------------------------------------------------------------------------


class TestMakeArticleDict:
    def test_cjeu_source_url(self) -> None:
        d = _make_article_dict("Facts", "Some text here.", _SCHREMS_META, "cjeu")
        assert "eur-lex.europa.eu" in d["source_url"]

    def test_echr_source_url(self) -> None:
        d = _make_article_dict("Facts", "Some text here.", _ECHR_META, "echr")
        assert "hudoc.echr.coe.int" in d["source_url"]

    def test_article_id_slug(self) -> None:
        d = _make_article_dict("Background and Facts", "text", _SCHREMS_META, "cjeu")
        assert " " not in d["article"]
        assert d["article"] == "background_and_facts"

    def test_required_fields_present(self) -> None:
        d = _make_article_dict("Title", "Body text.", _SCHREMS_META, "cjeu")
        for field in ("article", "title", "text", "celex_id", "regulation",
                      "published_date", "effective_date", "source_url"):
            assert field in d, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Integration: chunk_articles accepts caselaw output
# ---------------------------------------------------------------------------


class TestCaselawChunking:
    def test_chunk_articles_accepts_cjeu_output(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_ELI_HTML, _SCHREMS_META)
        chunks = chunk_articles(articles)
        assert len(chunks) >= 1

    def test_chunk_articles_accepts_echr_output(self) -> None:
        articles = fetch_echr_cases_from_html(_ECHR_HTML, _ECHR_META)
        chunks = chunk_articles(articles)
        assert len(chunks) >= 1

    def test_chunks_have_valid_regulation(self) -> None:
        articles = fetch_cjeu_cases_from_html(_CJEU_ELI_HTML, _SCHREMS_META)
        chunks = chunk_articles(articles)
        for chunk in chunks:
            assert chunk.regulation == "GDPR"


# ---------------------------------------------------------------------------
# fetch_cjeu_cases — HTTP mocked
# ---------------------------------------------------------------------------


class TestFetchCjeuCasesHttp:
    def test_returns_articles_on_success(self) -> None:
        mock_resp = MagicMock()
        mock_resp.text = _CJEU_ELI_HTML
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_resp)

        one_case = [_SCHREMS_META]
        with patch("lios.ingestion.caselaw_fetcher.httpx.Client", return_value=mock_client):
            articles = fetch_cjeu_cases(case_list=one_case)

        assert len(articles) >= 1

    def test_skips_on_http_error(self) -> None:
        import httpx as _httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(
            side_effect=_httpx.RequestError("timeout", request=MagicMock())
        )

        one_case = [_SCHREMS_META]
        with patch("lios.ingestion.caselaw_fetcher.httpx.Client", return_value=mock_client):
            articles = fetch_cjeu_cases(case_list=one_case)

        assert articles == []


# ---------------------------------------------------------------------------
# fetch_echr_cases — HTTP mocked
# ---------------------------------------------------------------------------


class TestFetchEchrCasesHttp:
    def test_returns_articles_on_success(self) -> None:
        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json = MagicMock(return_value=_HUDOC_SEARCH_RESPONSE)

        doc_resp = MagicMock()
        doc_resp.raise_for_status = MagicMock()
        doc_resp.text = _ECHR_HTML

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=[search_resp, doc_resp])

        one_topic = [ECHR_TOPICS[0]]
        with patch("lios.ingestion.caselaw_fetcher.httpx.Client", return_value=mock_client):
            articles = fetch_echr_cases(topics=one_topic, max_per_topic=1)

        assert len(articles) >= 1

    def test_skips_on_search_error(self) -> None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(side_effect=Exception("network error"))

        one_topic = [ECHR_TOPICS[0]]
        with patch("lios.ingestion.caselaw_fetcher.httpx.Client", return_value=mock_client):
            articles = fetch_echr_cases(topics=one_topic)

        assert articles == []

    def test_skips_result_missing_itemid(self) -> None:
        bad_response = {"results": [{"columns": {"docname": "No ID case"}}]}
        search_resp = MagicMock()
        search_resp.raise_for_status = MagicMock()
        search_resp.json = MagicMock(return_value=bad_response)

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=search_resp)

        one_topic = [ECHR_TOPICS[0]]
        with patch("lios.ingestion.caselaw_fetcher.httpx.Client", return_value=mock_client):
            articles = fetch_echr_cases(topics=one_topic)

        assert articles == []


# ---------------------------------------------------------------------------
# CJEU_CASES sanity checks
# ---------------------------------------------------------------------------


class TestCjeuCaseRegistry:
    def test_all_cases_have_required_fields(self) -> None:
        for case in CJEU_CASES:
            for field in ("celex_id", "case_num", "title", "regulation",
                          "published_date", "effective_date"):
                assert field in case, f"{case} missing {field}"

    def test_regulations_are_known(self) -> None:
        known = {"GDPR", "CSRD", "ESRS", "EU_TAXONOMY", "SFDR"}
        for case in CJEU_CASES:
            assert case["regulation"] in known, (
                f"{case['case_num']} has unknown regulation {case['regulation']!r}"
            )
