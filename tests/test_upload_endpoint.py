from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from lios.api.routes import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_upload_rejects_unsupported_format(client: TestClient) -> None:
    resp = client.post(
        "/api/upload",
        files={"file": ("dataset.zip", b"binary", "application/zip")},
    )
    assert resp.status_code == 415
    assert "Supported formats" in resp.json()["detail"]


def test_upload_accepts_mobile_octet_stream_with_pptx_filename(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from lios.ingestion import document_indexer

    monkeypatch.setattr(
        document_indexer,
        "index_uploaded_document",
        lambda **kwargs: {  # noqa: ARG005
            "status": "indexed",
            "filename": kwargs["filename"],
            "chunks_added": 2,
            "regulation": kwargs["regulation"],
            "doc_id": "doc123",
        },
    )

    resp = client.post(
        "/api/upload",
        data={"regulation": "CUSTOM"},
        files={"file": ("deck.pptx", b"fake-pptx", "application/octet-stream")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "indexed"
    assert ".pptx" in data["supported_formats"]


def test_upload_rejects_empty_files(client: TestClient) -> None:
    resp = client.post(
        "/api/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()
