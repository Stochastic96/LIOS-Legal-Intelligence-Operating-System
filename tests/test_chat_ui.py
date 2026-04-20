"""Tests for local chat studio endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from lios.api import routes
from lios.features.chat_training import LocalTrainingStore


def test_chat_page_renders() -> None:
    client = TestClient(routes.app)
    response = client.get("/chat")
    assert response.status_code == 200
    assert "LIOS Chat Studio" in response.text


def test_chat_react_page_renders() -> None:
    client = TestClient(routes.app)
    response = client.get("/chat-react")
    assert response.status_code == 200
    assert "LIOS React Chat Studio" in response.text


def test_root_redirects_to_chat() -> None:
    client = TestClient(routes.app)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/chat"


def test_chat_alias_redirects_to_chat() -> None:
    client = TestClient(routes.app)
    response = client.get("/chat-ui", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/chat"


def test_debug_routes_lists_chat_path() -> None:
    import os

    os.environ["LIOS_DEV_MODE"] = "true"
    # Recreate settings to pick up the env var
    from lios.config import settings as _settings
    _settings.DEV_MODE = True

    client = TestClient(routes.app)
    response = client.get("/debug/routes")
    assert response.status_code == 200
    payload = response.json()
    assert "/chat" in payload["routes"]
    assert "/chat-react" in payload["routes"]

    _settings.DEV_MODE = False
    os.environ.pop("LIOS_DEV_MODE", None)


def test_favicon_returns_no_content() -> None:
    client = TestClient(routes.app)
    response = client.get("/favicon.ico")
    assert response.status_code == 204


def test_chat_message_history_and_export(tmp_path: Path) -> None:
    routes._training_store = LocalTrainingStore(tmp_path / "chat_training.jsonl")
    client = TestClient(routes.app)

    msg = client.post(
        "/chat/api/message",
        json={
            "query": "Does CSRD apply to a company with 600 employees?",
            "session_id": "test-session-1",
            "company_profile": {"employees": 600, "turnover_eur": 50_000_000},
            "jurisdictions": ["Germany"],
        },
    )
    assert msg.status_code == 200
    payload = msg.json()
    assert payload["session_id"] == "test-session-1"
    assert payload["answer"]
    assert "mode" in payload
    assert "agent_count" in payload["mode"]
    assert isinstance(payload["citations"], list)
    if payload["citations"]:
        assert "url" in payload["citations"][0]

    hist = client.get("/chat/api/history", params={"session_id": "test-session-1"})
    assert hist.status_code == 200
    turns = hist.json()["turns"]
    assert len(turns) >= 1
    assert turns[-1]["session_id"] == "test-session-1"

    exported = client.get("/chat/api/export", params={"session_id": "test-session-1"})
    assert exported.status_code == 200
    assert "test-session-1" in exported.text
