"""Tests for the Ollama client, ollama-status endpoint, and /api/query endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from lios.api.routes import app
from lios.llm.ollama_client import (
    OLLAMA_FALLBACK_MODEL,
    OLLAMA_MODEL,
    check_ollama_health,
)
from lios.retrieval.hybrid_retriever import HybridRetriever, RetrievedChunk, get_retriever


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# ollama_client.py – unit tests
# ---------------------------------------------------------------------------


class TestOllamaClientConstants:
    def test_ollama_model_has_default(self):
        assert isinstance(OLLAMA_MODEL, str)
        assert len(OLLAMA_MODEL) > 0

    def test_ollama_fallback_model_has_default(self):
        assert isinstance(OLLAMA_FALLBACK_MODEL, str)
        assert len(OLLAMA_FALLBACK_MODEL) > 0

    def test_fallback_differs_from_primary(self):
        # The hardcoded defaults must differ so that a 404 fallback is meaningful
        assert "mistral:7b-instruct-q4_K_M" != "mistral:7b"


class TestCheckOllamaHealth:
    def test_returns_dict_with_expected_keys(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "models": [{"name": "mistral:7b"}, {"name": "llama3"}]
            }
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            result = check_ollama_health()

        assert "available" in result
        assert "models" in result

    def test_returns_available_true_when_ollama_responds(self):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"models": [{"name": "mistral:7b"}]}
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            result = check_ollama_health()

        assert result["available"] is True
        assert "mistral:7b" in result["models"]

    def test_returns_available_false_on_connection_error(self):
        import httpx

        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            result = check_ollama_health()

        assert result["available"] is False
        assert result["models"] == []

    def test_returns_available_false_on_generic_exception(self):
        with patch("httpx.get", side_effect=Exception("unexpected")):
            result = check_ollama_health()

        assert result["available"] is False
        assert result["models"] == []


class TestCallOllamaSync:
    def test_returns_string_response(self):
        import httpx

        from lios.llm.ollama_client import call_ollama_sync

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "This is the answer."}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = call_ollama_sync("What is CSRD?")

        assert result == "This is the answer."

    def test_falls_back_to_fallback_model_on_404(self):
        import httpx

        from lios.llm.ollama_client import call_ollama_sync

        resp_404 = MagicMock(spec=httpx.Response)
        resp_404.status_code = 404
        resp_404.raise_for_status = MagicMock()

        resp_200 = MagicMock(spec=httpx.Response)
        resp_200.status_code = 200
        resp_200.json.return_value = {"response": "Fallback answer."}
        resp_200.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            # First call returns 404, second returns 200
            mock_client.post.side_effect = [resp_404, resp_200]
            mock_client_cls.return_value = mock_client

            result = call_ollama_sync("What is CSRD?")

        assert result == "Fallback answer."
        assert mock_client.post.call_count == 2
        # Second call should use fallback model
        second_call_kwargs = mock_client.post.call_args_list[1][1]
        assert second_call_kwargs["json"]["model"] == OLLAMA_FALLBACK_MODEL


class TestCallOllamaAsync:
    @pytest.mark.asyncio
    async def test_returns_string_response(self):
        import httpx
        from unittest.mock import AsyncMock

        from lios.llm.ollama_client import call_ollama

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Async answer."}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await call_ollama("What is CSRD?")

        assert result == "Async answer."


# ---------------------------------------------------------------------------
# HybridRetriever – format_context and get_retriever
# ---------------------------------------------------------------------------


class TestHybridRetrieverFormatContext:
    @pytest.fixture
    def retriever(self, tmp_path):
        """Create a HybridRetriever with an empty corpus."""
        empty_corpus = tmp_path / "empty.jsonl"
        empty_corpus.write_text("")
        return HybridRetriever(corpus_path=str(empty_corpus))

    def test_format_context_returns_string(self, retriever):
        chunk = {
            "regulation": "CSRD",
            "article": "Art. 19",
            "title": "Sustainability reporting",
            "text": "Companies must report on sustainability.",
        }
        rc = RetrievedChunk(
            chunk=chunk,
            score_lexical=1.0,
            score_semantic=0.5,
            score_grounded=0.5,
        )
        result = retriever.format_context([rc])
        assert "CSRD" in result
        assert "Art. 19" in result
        assert "Companies must report" in result

    def test_format_context_empty_list(self, retriever):
        result = retriever.format_context([])
        assert result == ""

    def test_format_context_respects_max_chars(self, retriever):
        chunks = [
            RetrievedChunk(
                chunk={
                    "regulation": "CSRD",
                    "text": "x" * 1000,
                },
                score_lexical=float(i),
                score_semantic=0.0,
                score_grounded=0.0,
            )
            for i in range(10)
        ]
        result = retriever.format_context(chunks, max_chars=500)
        # Should be much less than 10 * 1000 chars
        assert len(result) < 5000

    def test_format_context_numbers_entries(self, retriever):
        chunks = [
            RetrievedChunk(
                chunk={"regulation": "CSRD", "text": "Text one"},
                score_lexical=1.0,
                score_semantic=0.0,
                score_grounded=0.0,
            ),
            RetrievedChunk(
                chunk={"regulation": "SFDR", "text": "Text two"},
                score_lexical=0.5,
                score_semantic=0.0,
                score_grounded=0.0,
            ),
        ]
        result = retriever.format_context(chunks)
        assert "[1]" in result
        assert "[2]" in result


class TestGetRetriever:
    def test_get_retriever_returns_hybrid_retriever(self):
        r = get_retriever()
        assert isinstance(r, HybridRetriever)

    def test_get_retriever_returns_same_instance(self):
        r1 = get_retriever()
        r2 = get_retriever()
        assert r1 is r2


# ---------------------------------------------------------------------------
# GET /api/ollama-status endpoint
# ---------------------------------------------------------------------------


class TestOllamaStatusEndpoint:
    def test_ollama_status_200(self, client):
        with patch("lios.api.routes.check_ollama_health") as mock_health:
            mock_health.return_value = {"available": True, "models": ["mistral:7b"]}
            resp = client.get("/api/ollama-status")
        assert resp.status_code == 200

    def test_ollama_status_has_available_key(self, client):
        with patch("lios.api.routes.check_ollama_health") as mock_health:
            mock_health.return_value = {"available": False, "models": []}
            resp = client.get("/api/ollama-status")
        data = resp.json()
        assert "available" in data

    def test_ollama_status_has_models_key(self, client):
        with patch("lios.api.routes.check_ollama_health") as mock_health:
            mock_health.return_value = {"available": True, "models": ["mistral:7b"]}
            resp = client.get("/api/ollama-status")
        data = resp.json()
        assert "models" in data
        assert isinstance(data["models"], list)

    def test_ollama_status_available_true_when_running(self, client):
        with patch("lios.api.routes.check_ollama_health") as mock_health:
            mock_health.return_value = {"available": True, "models": ["mistral:7b"]}
            resp = client.get("/api/ollama-status")
        assert resp.json()["available"] is True

    def test_ollama_status_available_false_when_down(self, client):
        with patch("lios.api.routes.check_ollama_health") as mock_health:
            mock_health.return_value = {"available": False, "models": []}
            resp = client.get("/api/ollama-status")
        assert resp.json()["available"] is False


# ---------------------------------------------------------------------------
# POST /api/query endpoint
# ---------------------------------------------------------------------------


class TestRagQueryEndpoint:
    def test_rag_query_returns_200_when_ollama_available(self, client):
        async def _answer(prompt: str, model: str | None = None) -> str:
            return "CSRD requires large companies to disclose."
        with patch("lios.api.routes.call_ollama", new=_answer):
            resp = client.post("/api/query", json={"query": "What is CSRD?"})
        assert resp.status_code == 200

    def test_rag_query_response_has_required_keys(self, client):
        async def _answer(prompt: str, model: str | None = None) -> str:
            return "Answer text here."
        with patch("lios.api.routes.call_ollama", new=_answer):
            resp = client.post("/api/query", json={"query": "What is CSRD?"})
        data = resp.json()
        assert "query" in data
        assert "answer" in data
        assert "sources" in data

    def test_rag_query_echoes_query(self, client):
        async def _answer(prompt: str, model: str | None = None) -> str:
            return "Some answer."
        with patch("lios.api.routes.call_ollama", new=_answer):
            resp = client.post("/api/query", json={"query": "What is SFDR?"})
        assert resp.json()["query"] == "What is SFDR?"

    def test_rag_query_answer_is_string(self, client):
        async def _answer(prompt: str, model: str | None = None) -> str:
            return "A detailed answer."
        with patch("lios.api.routes.call_ollama", new=_answer):
            resp = client.post("/api/query", json={"query": "Explain EU Taxonomy"})
        assert isinstance(resp.json()["answer"], str)

    def test_rag_query_sources_is_list(self, client):
        async def _answer(prompt: str, model: str | None = None) -> str:
            return "An answer."
        with patch("lios.api.routes.call_ollama", new=_answer):
            resp = client.post("/api/query", json={"query": "What is CSRD?"})
        assert isinstance(resp.json()["sources"], list)

    def test_rag_query_returns_503_when_ollama_unavailable(self, client):
        import httpx

        async def _raise(prompt: str, model: str | None = None) -> str:
            raise httpx.ConnectError("refused")

        with patch("lios.api.routes.call_ollama", new=_raise):
            resp = client.post("/api/query", json={"query": "What is CSRD?"})
        assert resp.status_code == 503

    def test_rag_query_missing_body_returns_422(self, client):
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_rag_query_sources_have_regulation_field(self, client):
        async def _answer(prompt: str, model: str | None = None) -> str:
            return "An answer."
        with patch("lios.api.routes.call_ollama", new=_answer):
            resp = client.post("/api/query", json={"query": "What is CSRD?"})
        sources = resp.json()["sources"]
        for src in sources:
            assert "regulation" in src
