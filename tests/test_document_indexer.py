from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from lios.ingestion import document_indexer


def test_detect_upload_format_supports_pptx_and_xlsx() -> None:
    assert document_indexer.detect_upload_format("slides.pptx", "") == "pptx"
    assert document_indexer.detect_upload_format("financials.xlsx", "") == "xlsx"


def test_detect_upload_format_rejects_unsupported() -> None:
    with pytest.raises(document_indexer.UnsupportedDocumentFormatError):
        document_indexer.detect_upload_format("archive.zip", "application/zip")


def test_extract_text_pptx(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Shape:
        def __init__(self, text: str):
            self.text = text

    class _Slide:
        def __init__(self, texts: list[str]):
            self.shapes = [_Shape(t) for t in texts]

    class _Presentation:
        def __init__(self, _stream):
            self.slides = [_Slide(["Quarterly Results", "Revenue up"]), _Slide(["Outlook"])]

    fake_pptx = types.SimpleNamespace(Presentation=_Presentation)
    monkeypatch.setitem(sys.modules, "pptx", fake_pptx)

    text = document_indexer._extract_text(b"fake", "deck.pptx", "application/octet-stream")
    assert "Quarterly Results" in text
    assert "Outlook" in text


def test_extract_text_xlsx(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Sheet:
        title = "Sheet1"

        def iter_rows(self, values_only=True):  # noqa: ARG002
            return [
                ("Company", "Turnover", None),
                ("Acme", 85000000, "EUR"),
            ]

    class _Workbook:
        worksheets = [_Sheet()]

    def _load_workbook(_stream, data_only=True, read_only=True):  # noqa: ARG001
        return _Workbook()

    fake_openpyxl = types.SimpleNamespace(load_workbook=_load_workbook)
    monkeypatch.setitem(sys.modules, "openpyxl", fake_openpyxl)

    text = document_indexer._extract_text(b"fake", "finance.xlsx", "application/octet-stream")
    assert "Sheet1" in text
    assert "Acme | 85000000 | EUR" in text


def test_index_uploaded_document_preserves_chunk_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus_path = tmp_path / "legal_chunks.jsonl"
    monkeypatch.setattr(document_indexer, "_CORPUS_PATH", corpus_path)

    result = document_indexer.index_uploaded_document(
        content=b"This uploaded legal note explains obligations under CSRD.",
        filename="note.txt",
        content_type="text/plain",
        title="Internal CSRD Note",
        regulation="CUSTOM",
        source_description="user upload",
    )

    assert result["status"] == "indexed"
    payload = corpus_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(payload) == 1
    record = json.loads(payload[0])
    assert record["is_uploaded"] is True
    assert record["regulation"] == "CUSTOM"
    assert record["article"].startswith("upload-")
    assert record["celex_or_doc_id"] == result["doc_id"]
