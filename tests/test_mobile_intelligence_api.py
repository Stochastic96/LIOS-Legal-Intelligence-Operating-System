from __future__ import annotations

from fastapi.testclient import TestClient

from lios.api import routes
from lios.api.routers import intelligence as intelligence_router
from lios.config import settings


def _api_key_headers() -> dict[str, str]:
    return {"X-API-Key": settings.API_KEY} if settings.API_KEY_REQUIRED else {}


def test_intelligence_stats_include_consumed_files(tmp_path) -> None:
    corpus = tmp_path / "legal_chunks.jsonl"
    corpus.write_text(
        "\n".join(
            [
                '{"text":"A","regulation":"CSRD","article":"Art.1","filename":"CSRD.pdf"}',
                '{"text":"B","regulation":"CSRD","article":"Art.2","filename":"CSRD.pdf"}',
                '{"text":"C","regulation":"GDPR","article":"Art.3","filename":"GDPR.pdf"}',
            ]
        ),
        encoding="utf-8",
    )

    original_corpus = intelligence_router._CORPUS_FILE
    intelligence_router._CORPUS_FILE = corpus
    client = TestClient(routes.app)

    try:
        response = client.get("/intelligence/stats", headers=_api_key_headers())
        assert response.status_code == 200
        payload = response.json()
        assert payload["total_chunks"] == 3
        assert payload["consumed_files"] == 2
    finally:
        intelligence_router._CORPUS_FILE = original_corpus


def test_intelligence_files_support_name_only_search(tmp_path) -> None:
    corpus = tmp_path / "legal_chunks.jsonl"
    corpus.write_text(
        "\n".join(
            [
                '{"text":"A","regulation":"CSRD","article":"Art.1","filename":"CSRD_2022-2464.pdf","source_url":"https://example.com/csrd"}',
                '{"text":"B","regulation":"CSRD","article":"Art.2","filename":"CSRD_2022-2464.pdf"}',
                '{"text":"C","regulation":"CJEU_FRANCOVICH","article":"Art.3","filename":"Francovich_1991.pdf"}',
            ]
        ),
        encoding="utf-8",
    )

    original_corpus = intelligence_router._CORPUS_FILE
    intelligence_router._CORPUS_FILE = corpus
    client = TestClient(routes.app)

    try:
        response = client.get(
            "/intelligence/files",
            headers=_api_key_headers(),
            params={"query": "franc", "limit": 10},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "franc"
        assert payload["total"] == 1
        assert payload["files"][0]["filename"] == "Francovich_1991.pdf"
        assert payload["files"][0]["chunk_count"] == 1

        all_files = client.get("/intelligence/files", headers=_api_key_headers(), params={"limit": 10})
        all_payload = all_files.json()
        assert all_payload["total"] == 2
        assert all_payload["files"][0]["filename"] == "CSRD_2022-2464.pdf"
        assert all_payload["files"][0]["article_count"] == 2
    finally:
        intelligence_router._CORPUS_FILE = original_corpus
