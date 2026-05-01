from __future__ import annotations

from lios.llm.refiner import LLMRefiner, settings


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": self._content,
                    }
                }
            ]
        }


class _FakeClient:
    last_request: dict[str, object] | None = None

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def post(self, endpoint: str, headers=None, json=None):
        type(self).last_request = {
            "endpoint": endpoint,
            "headers": headers,
            "json": json,
        }
        return _FakeResponse("Mistral refined answer")


def test_llm_refiner_uses_openai_compatible_httpx(monkeypatch) -> None:
    monkeypatch.setattr(settings, "LLM_ENABLED", True)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr(settings, "LLM_MODEL", "mistral")
    monkeypatch.setattr(settings, "LLM_API_KEY", "ollama")
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 5)
    monkeypatch.setattr("lios.llm.refiner.httpx.Client", _FakeClient)

    refiner = LLMRefiner()
    answer = refiner.refine("What is CSRD?", "Draft answer", {"intent": "general_query"})

    assert answer == "Mistral refined answer"
    assert _FakeClient.last_request is not None
    assert _FakeClient.last_request["endpoint"] == "http://localhost:11434/v1/chat/completions"
    assert _FakeClient.last_request["json"]["model"] == "mistral"


def test_llm_refiner_returns_draft_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "LLM_ENABLED", False)
    refiner = LLMRefiner()
    assert refiner.refine("What is CSRD?", "Draft answer") == "Draft answer"