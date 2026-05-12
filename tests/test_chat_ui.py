"""Tests for local chat studio endpoints."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from lios.api import routes
from lios.api.routers import chat as chat_router
from lios.config import settings
from lios.features.chat_training import LocalTrainingStore


def _api_key_headers() -> dict[str, str]:
    return {"X-API-Key": settings.API_KEY} if settings.API_KEY_REQUIRED else {}


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
    original_store_router = chat_router.training_store
    original_store_routes = routes._training_store
    store = LocalTrainingStore(tmp_path / "chat_training.jsonl")
    chat_router.training_store = store
    routes._training_store = store
    client = TestClient(routes.app)

    try:
        msg = client.post(
            "/chat/api/message",
            headers=_api_key_headers(),
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

        hist = client.get(
            "/chat/api/history", headers=_api_key_headers(), params={"session_id": "test-session-1"}
        )
        assert hist.status_code == 200
        turns = hist.json()["turns"]
        assert len(turns) >= 1
        assert turns[-1]["session_id"] == "test-session-1"

        exported = client.get(
            "/chat/api/export", headers=_api_key_headers(), params={"session_id": "test-session-1"}
        )
        assert exported.status_code == 200
        assert "test-session-1" in exported.text
    finally:
        chat_router.training_store = original_store_router
        routes._training_store = original_store_routes


def test_mobile_chat_alias_uses_shared_contract_and_history(tmp_path: Path) -> None:
    original_engine = chat_router.engine
    original_store_router = chat_router.training_store
    original_store_routes = routes._training_store
    store = LocalTrainingStore(tmp_path / "chat_training.jsonl")
    chat_router.training_store = store
    routes._training_store = store
    chat_router.engine = SimpleNamespace(
        route_query=lambda **_: SimpleNamespace(
            answer="CSRD applies.",
            intent="applicability",
            question_type="APPLICABILITY",
            citations=[
                SimpleNamespace(
                    regulation="CSRD",
                    article_id="Art.2",
                    title="Scope",
                    relevance_score=91,
                    url="https://eur-lex.europa.eu",
                )
            ],
            consensus_result=SimpleNamespace(
                consensus_reached=True, confidence=0.82, agent_responses=[object(), object()]
            ),
            grounding_score=0.82,
        )
    )
    client = TestClient(routes.app)

    try:
        response = client.post(
            "/chat",
            headers=_api_key_headers(),
            json={"query": "Does CSRD apply?", "session_id": "mobile-s1"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == "mobile-s1"
        assert payload["answer"] == "CSRD applies."
        assert payload["citations"][0]["regulation"] == "CSRD"
        assert payload["confidence"] == "high"
        assert payload["confidence_score"] == 0.82
        assert payload["source"] == "applicability"
        assert payload["message_id"]
        assert isinstance(payload["brain_used"], bool)

        history = client.get("/chat/history/mobile-s1", headers=_api_key_headers())
        assert history.status_code == 200
        turns = history.json()["turns"]
        assert len(turns) >= 1
        assert turns[-1]["session_id"] == "mobile-s1"
        assert turns[-1]["answer"] == "CSRD applies."
    finally:
        chat_router.engine = original_engine
        chat_router.training_store = original_store_router
        routes._training_store = original_store_routes


def test_chat_contract_handles_missing_citations_and_uses_consensus_confidence(tmp_path: Path) -> None:
    original_engine = chat_router.engine
    original_store_router = chat_router.training_store
    store = LocalTrainingStore(tmp_path / "chat_training.jsonl")
    chat_router.training_store = store
    chat_router.engine = SimpleNamespace(
        route_query=lambda **_: SimpleNamespace(
            answer="Fallback answer",
            intent="general_law",
            citations=None,
            consensus_result=SimpleNamespace(
                consensus_reached=False, confidence=0.61, agent_responses=[object()]
            ),
        )
    )
    client = TestClient(routes.app)

    try:
        response = client.post(
            "/chat/api/message",
            headers=_api_key_headers(),
            json={"query": "Test question", "session_id": "session-fallback"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["citations"] == []
        assert payload["confidence"] == 0.61
        assert payload["grounding"] == "medium"
        assert payload["consensus"]["confidence"] == 0.61
    finally:
        chat_router.engine = original_engine
        chat_router.training_store = original_store_router


def test_chat_endpoints_return_predictable_errors_on_engine_failure(tmp_path: Path) -> None:
    original_engine = chat_router.engine
    original_store_router = chat_router.training_store
    store = LocalTrainingStore(tmp_path / "chat_training.jsonl")
    chat_router.training_store = store
    chat_router.engine = SimpleNamespace(route_query=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")))
    client = TestClient(routes.app)

    try:
        web = client.post(
            "/chat/api/message", headers=_api_key_headers(), json={"query": "Fail", "session_id": "s-fail"}
        )
        assert web.status_code == 500
        assert web.json()["detail"] == {"error": "Failed to process chat message"}

        mobile = client.post(
            "/chat",
            headers=_api_key_headers(),
            json={"query": "Fail", "session_id": "m-fail"},
        )
        assert mobile.status_code == 500
        assert mobile.json()["detail"] == {"error": "Failed to process chat message"}
    finally:
        chat_router.engine = original_engine
        chat_router.training_store = original_store_router
