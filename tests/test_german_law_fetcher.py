"""Offline tests for the German national law fetcher.

All HTTP calls are mocked; no real network or ZIP access is required.
"""

from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from lios.ingestion.german_law_fetcher import (
    GERMAN_LAWS,
    fetch_german_laws,
    parse_german_law_xml,
    parse_german_law_zip,
    _parse_norm,
    _extract_norm_text,
)
from lios.ingestion.legal_chunker import chunk_articles

# ---------------------------------------------------------------------------
# XML fixtures (minimal but structurally correct)
# ---------------------------------------------------------------------------

_NORM_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dokumente>
  <norm>
    <metadaten>
      <jurabk>HGB</jurabk>
      <enbez>&#167; 1</enbez>
      <titel>Istkaufmann</titel>
    </metadaten>
    <textdaten>
      <text format="XML">
        <Content>
          <P>Kaufmann im Sinne dieses Gesetzbuches ist, wer ein Handelsgewerbe
          betreibt.</P>
          <P>Als Handelsgewerbe gilt jeder Gewerbebetrieb, es sei denn, dass das
          Unternehmen nach Art oder Umfang einen in kaufmaennischer Weise
          eingerichteten Geschaeftsbetrieb nicht erfordert.</P>
        </Content>
      </text>
    </textdaten>
  </norm>
  <norm>
    <metadaten>
      <jurabk>HGB</jurabk>
      <enbez>&#167; 2</enbez>
      <titel>Kannkaufmann</titel>
    </metadaten>
    <textdaten>
      <text format="XML">
        <Content>
          <P>Ein gewerbliches Unternehmen, das nach Art und Umfang einen in
          kaufmaennischer Weise eingerichteten Geschaeftsbetrieb erfordert,
          dessen Inhaber aber nicht bereits nach Paragraf 1 Kaufmann ist, gilt als
          Handelsgewerbe im Sinne dieses Gesetzbuches, wenn die Firma des
          Inhabers in das Handelsregister eingetragen ist.</P>
        </Content>
      </text>
    </textdaten>
  </norm>
  <norm>
    <metadaten>
      <jurabk>HGB</jurabk>
      <enbez>Inhaltsübersicht</enbez>
    </metadaten>
    <textdaten>
      <text format="XML"><Content><P>Table of contents placeholder</P></Content></text>
    </textdaten>
  </norm>
</dokumente>
""".encode("utf-8")

_HGB_META = {
    "regulation": "HGB",
    "full_name": "Handelsgesetzbuch",
    "jurisdiction": "Germany",
    "published_date": "1897-05-10",
    "effective_date": "1900-01-01",
}


def _make_zip(xml_bytes: bytes, filename: str = "BJNR001970897.xml") -> bytes:
    """Create an in-memory ZIP containing *xml_bytes*."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, xml_bytes)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# parse_german_law_xml
# ---------------------------------------------------------------------------


class TestParseGermanLawXml:
    def test_extracts_section_norms(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        assert len(articles) == 2

    def test_skips_toc_entries(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        titles = [a["title"] for a in articles]
        assert not any("bersicht" in t for t in titles)

    def test_regulation_set(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        assert all(a["regulation"] == "HGB" for a in articles)

    def test_celex_id_format(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        for a in articles:
            assert a["celex_id"].startswith("HGB:")

    def test_source_url_set(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        for a in articles:
            assert "gesetze-im-internet.de" in a["source_url"]

    def test_article_id_no_spaces(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        for a in articles:
            assert " " not in a["article"]

    def test_text_is_non_empty(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        for a in articles:
            assert len(a["text"]) >= 30

    def test_required_fields_present(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        for a in articles:
            for field in ("article", "title", "text", "celex_id", "regulation",
                          "published_date", "effective_date"):
                assert field in a, f"Missing {field}"

    def test_handles_invalid_xml_gracefully(self) -> None:
        articles = parse_german_law_xml(b"<not valid xml", "hgb", _HGB_META)
        assert articles == []

    def test_handles_empty_xml(self) -> None:
        empty_xml = b'<?xml version="1.0"?><dokumente></dokumente>'
        articles = parse_german_law_xml(empty_xml, "hgb", _HGB_META)
        assert articles == []


# ---------------------------------------------------------------------------
# parse_german_law_zip
# ---------------------------------------------------------------------------


class TestParseGermanLawZip:
    def test_extracts_from_valid_zip(self) -> None:
        zip_bytes = _make_zip(_NORM_XML)
        articles = parse_german_law_zip(zip_bytes, "hgb", _HGB_META)
        assert len(articles) == 2

    def test_handles_bad_zip(self) -> None:
        articles = parse_german_law_zip(b"not a zip", "hgb", _HGB_META)
        assert articles == []

    def test_handles_zip_without_xml(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "no xml here")
        articles = parse_german_law_zip(buf.getvalue(), "hgb", _HGB_META)
        assert articles == []


# ---------------------------------------------------------------------------
# Integration with chunk_articles
# ---------------------------------------------------------------------------


class TestGermanLawChunking:
    def test_chunk_articles_accepts_german_output(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        chunks = chunk_articles(articles)
        assert len(chunks) >= 1

    def test_chunks_have_correct_regulation(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        chunks = chunk_articles(articles)
        for chunk in chunks:
            assert chunk.regulation == "HGB"

    def test_chunks_jurisdiction_germany(self) -> None:
        articles = parse_german_law_xml(_NORM_XML, "hgb", _HGB_META)
        chunks = chunk_articles(articles)
        for chunk in chunks:
            assert chunk.jurisdiction == "Germany"


# ---------------------------------------------------------------------------
# fetch_german_laws — HTTP mocked
# ---------------------------------------------------------------------------


class TestFetchGermanLawsHttp:
    def test_returns_articles_on_success(self) -> None:
        zip_bytes = _make_zip(_NORM_XML)
        mock_resp = MagicMock()
        mock_resp.content = zip_bytes
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(return_value=mock_resp)

        with patch("lios.ingestion.german_law_fetcher.httpx.Client", return_value=mock_client):
            articles = fetch_german_laws(law_keys=["hgb"])

        assert len(articles) >= 1

    def test_skips_on_http_error(self) -> None:
        import httpx as _httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get = MagicMock(
            side_effect=_httpx.RequestError("timeout", request=MagicMock())
        )

        with patch("lios.ingestion.german_law_fetcher.httpx.Client", return_value=mock_client):
            articles = fetch_german_laws(law_keys=["hgb"])

        assert articles == []

    def test_skips_unknown_law_key(self) -> None:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("lios.ingestion.german_law_fetcher.httpx.Client", return_value=mock_client):
            articles = fetch_german_laws(law_keys=["unknownlaw"])

        assert articles == []
        mock_client.get.assert_not_called()


# ---------------------------------------------------------------------------
# GERMAN_LAWS registry sanity checks
# ---------------------------------------------------------------------------


class TestGermanLawRegistry:
    def test_all_entries_have_required_fields(self) -> None:
        for abbrev, meta in GERMAN_LAWS.items():
            for field in ("regulation", "full_name", "jurisdiction",
                          "published_date", "effective_date"):
                assert field in meta, f"{abbrev} missing {field}"

    def test_jurisdictions_are_germany(self) -> None:
        for meta in GERMAN_LAWS.values():
            assert meta["jurisdiction"] == "Germany"

    def test_at_least_six_laws_registered(self) -> None:
        assert len(GERMAN_LAWS) >= 6
