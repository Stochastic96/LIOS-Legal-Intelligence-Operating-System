"""Offline unit tests for lios/ingestion/german_law_pipeline.py.

All HTTP calls are mocked — no real network access is required.
"""

from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lios.ingestion.german_law_pipeline import (
    GERMAN_LAWS,
    _load_existing_prefixes,
    fetch_law,
    ingest_german_laws,
    parse_law_xml,
    parse_law_zip,
)

# ---------------------------------------------------------------------------
# Helpers to build synthetic XML ZIPs
# ---------------------------------------------------------------------------

_SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<dokument>
  <norm builddate="20240101" doknr="BJNR001950896">
    <metadaten>
      <jurabk>BGB</jurabk>
    </metadaten>
    <textdaten>
      <fussnoten>
        <Content><P>Einleitungstext</P></Content>
      </fussnoten>
    </textdaten>
  </norm>
  <norm builddate="20240101" doknr="BJNR001950896BJNE000100377">
    <metadaten>
      <jurabk>BGB</jurabk>
      <enbez>§ 1</enbez>
      <titel format="parat">Rechtsfähigkeit des Menschen</titel>
    </metadaten>
    <textdaten>
      <text format="XML">
        <Content>
          <P>Die Rechtsfähigkeit des Menschen beginnt mit der Vollendung der Geburt.</P>
        </Content>
      </text>
    </textdaten>
  </norm>
  <norm builddate="20240101" doknr="BJNR001950896BJNE000200377">
    <metadaten>
      <jurabk>BGB</jurabk>
      <enbez>§ 2</enbez>
      <titel format="parat">Eintritt der Volljährigkeit</titel>
    </metadaten>
    <textdaten>
      <text format="XML">
        <Content>
          <P>Die Volljährigkeit tritt mit der Vollendung des 18. Lebensjahres ein.</P>
        </Content>
      </text>
    </textdaten>
  </norm>
  <norm builddate="20240101" doknr="BJNR001950896BJNE000300377">
    <metadaten>
      <jurabk>BGB</jurabk>
      <enbez>§ 3</enbez>
    </metadaten>
    <textdaten>
      <text format="XML">
        <Content>
          <P>(weggefallen)</P>
        </Content>
      </text>
    </textdaten>
  </norm>
</dokument>
"""

_SAMPLE_XML_NAMESPACE = """\
<?xml version="1.0" encoding="UTF-8"?>
<dokument>
  <norm builddate="20240101" doknr="TEST001">
    <metadaten>
      <enbez>§ 1</enbez>
      <titel format="parat">Allgemeine Bestimmungen</titel>
    </metadaten>
    <textdaten>
      <text format="XML">
        <Content xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <P>Erster Absatz des Gesetzes mit wichtigen Bestimmungen.</P>
          <P>Zweiter Absatz mit weiteren Einzelheiten.</P>
        </Content>
      </text>
    </textdaten>
  </norm>
</dokument>
"""


def _make_zip(xml_content: str, filename: str = "bgb.xml") -> bytes:
    """Build a ZIP archive containing *xml_content* as *filename*."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, xml_content.encode("utf-8"))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests for parse_law_xml
# ---------------------------------------------------------------------------


class TestParseLawXml:
    def test_extracts_paragraphs(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        assert len(chunks) >= 2

    def test_paragraph_ids_extracted(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        articles = {c["article"] for c in chunks}
        assert "§ 1" in articles
        assert "§ 2" in articles

    def test_text_contains_paragraph_content(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        texts = " ".join(c["text"] for c in chunks)
        assert "Rechtsfähigkeit" in texts

    def test_regulation_field_set(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        for c in chunks:
            assert c["regulation"] == "BGB"

    def test_jurisdiction_is_de(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        for c in chunks:
            assert c["jurisdiction"] == "DE"

    def test_source_field(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        for c in chunks:
            assert c["source"] == "gesetze-im-internet.de"

    def test_chunk_type_is_paragraph(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        for c in chunks:
            assert c["chunk_type"] == "paragraph"

    def test_celex_id_empty(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        for c in chunks:
            assert c["celex_id"] == ""

    def test_required_fields_present(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        required = {"text", "regulation", "article", "celex_id", "source", "jurisdiction", "chunk_type"}
        for c in chunks:
            assert required.issubset(c.keys())

    def test_skips_norm_without_enbez(self) -> None:
        # The first norm has no <enbez> — it should be skipped
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        articles = {c["article"] for c in chunks}
        # No empty-string article
        assert "" not in articles

    def test_namespace_in_content_handled(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML_NAMESPACE.encode("utf-8"), "TestLaw")
        assert len(chunks) == 1
        assert "Allgemeine Bestimmungen" in chunks[0]["text"]
        assert "Erster Absatz" in chunks[0]["text"]

    def test_invalid_xml_returns_empty(self) -> None:
        chunks = parse_law_xml(b"<not valid xml <<>>", "BGB")
        assert chunks == []

    def test_titel_included_in_text(self) -> None:
        chunks = parse_law_xml(_SAMPLE_XML.encode("utf-8"), "BGB")
        par1 = next(c for c in chunks if c["article"] == "§ 1")
        assert "Rechtsfähigkeit des Menschen" in par1["text"]


# ---------------------------------------------------------------------------
# Tests for parse_law_zip
# ---------------------------------------------------------------------------


class TestParseLawZip:
    def test_extracts_chunks_from_zip(self) -> None:
        zip_bytes = _make_zip(_SAMPLE_XML)
        chunks = parse_law_zip(zip_bytes, "BGB")
        assert len(chunks) >= 2

    def test_bad_zip_returns_empty(self) -> None:
        chunks = parse_law_zip(b"not a zip", "BGB")
        assert chunks == []

    def test_zip_without_xml_returns_empty(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "no xml here")
        chunks = parse_law_zip(buf.getvalue(), "BGB")
        assert chunks == []

    def test_selects_largest_xml(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("small.xml", b"<dokument/>")
            zf.writestr("bgb.xml", _SAMPLE_XML.encode("utf-8"))
        chunks = parse_law_zip(buf.getvalue(), "BGB")
        assert len(chunks) >= 2


# ---------------------------------------------------------------------------
# Tests for fetch_law (mocked HTTP)
# ---------------------------------------------------------------------------


class TestFetchLaw:
    def test_fetch_law_calls_correct_url(self) -> None:
        zip_bytes = _make_zip(_SAMPLE_XML)
        mock_resp = MagicMock()
        mock_resp.content = zip_bytes
        mock_resp.raise_for_status = MagicMock()

        with patch("lios.ingestion.german_law_pipeline.httpx") as mock_httpx:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_httpx.Client.return_value = mock_client

            chunks = fetch_law("bgb")

        call_args = mock_client.get.call_args[0][0]
        assert "bgb" in call_args
        assert "gesetze-im-internet.de" in call_args
        assert len(chunks) >= 2

    def test_fetch_law_http_error_returns_empty(self) -> None:
        with patch("lios.ingestion.german_law_pipeline.httpx") as mock_httpx:
            mock_httpx.HTTPStatusError = Exception
            mock_httpx.RequestError = ConnectionError
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = ConnectionError("network error")
            mock_httpx.Client.return_value = mock_client

            chunks = fetch_law("bgb")

        assert chunks == []

    def test_fetch_law_unknown_abbreviation_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown law abbreviation"):
            fetch_law("xyz_unknown")


# ---------------------------------------------------------------------------
# Tests for _load_existing_prefixes
# ---------------------------------------------------------------------------


class TestLoadExistingPrefixesGerman:
    def test_empty_when_no_file(self, tmp_path: Path) -> None:
        prefixes = _load_existing_prefixes(tmp_path / "missing.jsonl")
        assert prefixes == set()

    def test_reads_existing_text_prefixes(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        text = "§ 1 Rechtsfähigkeit des Menschen Die Rechtsfähigkeit beginnt"
        corpus.write_text(json.dumps({"text": text}) + "\n")
        prefixes = _load_existing_prefixes(corpus)
        assert text[:80] in prefixes


# ---------------------------------------------------------------------------
# Tests for ingest_german_laws
# ---------------------------------------------------------------------------


class TestIngestGermanLaws:
    def _mock_fetch(self, law_chunks: list[dict]) -> MagicMock:
        """Return a patch target that returns *law_chunks* for any abbreviation."""
        return patch(
            "lios.ingestion.german_law_pipeline.fetch_law",
            return_value=law_chunks,
        )

    def _sample_chunks(self) -> list[dict]:
        return [
            {
                "text": "§ 1 Rechtsfähigkeit des Menschen\nDie Rechtsfähigkeit des Menschen beginnt.",
                "regulation": "BGB",
                "article": "§ 1",
                "celex_id": "",
                "source": "gesetze-im-internet.de",
                "jurisdiction": "DE",
                "chunk_type": "paragraph",
            },
        ]

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        with self._mock_fetch(self._sample_chunks()):
            ingest_german_laws(laws=["bgb"], corpus_path=corpus, dry_run=True)
        assert not corpus.exists()

    def test_writes_chunks_to_jsonl(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        with self._mock_fetch(self._sample_chunks()):
            with patch("lios.retrieval.chroma_retriever.ingest_jsonl", return_value=0):
                count = ingest_german_laws(laws=["bgb"], corpus_path=corpus)
        assert count == 1
        lines = [l for l in corpus.read_text().splitlines() if l.strip()]
        assert len(lines) == 1

    def test_deduplication_prevents_double_write(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        with self._mock_fetch(self._sample_chunks()):
            with patch("lios.retrieval.chroma_retriever.ingest_jsonl", return_value=0):
                first = ingest_german_laws(laws=["bgb"], corpus_path=corpus)
                second = ingest_german_laws(laws=["bgb"], corpus_path=corpus)
        assert first == 1
        assert second == 0

    def test_unknown_law_skipped(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        # Should not raise, just print a warning
        ingest_german_laws(laws=["xyz_unknown"], corpus_path=corpus)
        assert not corpus.exists()

    def test_chunk_fields_in_jsonl(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        with self._mock_fetch(self._sample_chunks()):
            with patch("lios.retrieval.chroma_retriever.ingest_jsonl", return_value=0):
                ingest_german_laws(laws=["bgb"], corpus_path=corpus)
        chunk = json.loads(corpus.read_text().splitlines()[0])
        assert chunk["jurisdiction"] == "DE"
        assert chunk["source"] == "gesetze-im-internet.de"
        assert chunk["chunk_type"] == "paragraph"

    def test_default_laws_processes_all(self, tmp_path: Path) -> None:
        corpus = tmp_path / "corpus.jsonl"
        call_log: list[str] = []

        def fake_fetch(abbr: str) -> list[dict]:
            call_log.append(abbr)
            return []

        with patch("lios.ingestion.german_law_pipeline.fetch_law", side_effect=fake_fetch):
            ingest_german_laws(corpus_path=corpus)

        assert set(call_log) == set(GERMAN_LAWS.keys())
