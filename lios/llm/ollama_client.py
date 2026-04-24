"""Direct Ollama REST API client with configurable model, fallback, and health check."""

from __future__ import annotations

import logging
import os
from typing import Any

from lios.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration – all overridable via environment variables
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", settings.LLM_MODEL)
OLLAMA_FALLBACK_MODEL: str = os.getenv("OLLAMA_FALLBACK_MODEL", settings.LLM_MODEL)
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", str(settings.LLM_TIMEOUT_SECONDS)))


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


async def call_ollama(prompt: str, model: str | None = None) -> str:
    """Call the Ollama generate API asynchronously."""
    import httpx

    target_model = model or OLLAMA_MODEL
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload: dict[str, Any] = {
        "model": target_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(url, json=payload)

            if resp.status_code == 404 and target_model == OLLAMA_MODEL:
                logger.error(
                    "Model %r not found in Ollama. Run: ollama pull %s",
                    OLLAMA_MODEL,
                    OLLAMA_MODEL,
                )
                if OLLAMA_FALLBACK_MODEL != OLLAMA_MODEL:
                    logger.warning("Falling back to %r", OLLAMA_FALLBACK_MODEL)
                    payload["model"] = OLLAMA_FALLBACK_MODEL
                    resp = await client.post(url, json=payload)

            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except httpx.ConnectError as exc:
        logger.error("Cannot connect to Ollama at %s. Is it running? (ollama serve)", OLLAMA_BASE_URL)
        raise RuntimeError(f"Failed to call Ollama: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error in call_ollama: %s", exc)
        raise RuntimeError(f"Failed to call Ollama: {exc}") from exc


# ---------------------------------------------------------------------------
# Synchronous client
# ---------------------------------------------------------------------------


def call_ollama_sync(prompt: str, model: str | None = None) -> str:
    """Call the Ollama generate API synchronously.

    Uses httpx directly without asyncio so it can be called from both
    synchronous and asynchronous contexts without event-loop conflicts.

    Args:
        prompt: The prompt text to send.
        model:  Override the model name (defaults to ``OLLAMA_MODEL``).

    Returns:
        The generated text response from Ollama.

    Raises:
        httpx.ConnectError: When Ollama is unreachable.
        httpx.HTTPStatusError: On non-recoverable HTTP errors.
    """
    import httpx

    target_model = model or OLLAMA_MODEL
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload: dict[str, Any] = {
        "model": target_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            resp = client.post(url, json=payload)

            if resp.status_code == 404 and target_model == OLLAMA_MODEL:
                logger.error(
                    "Model %r not found in Ollama. Run: ollama pull %s",
                    OLLAMA_MODEL,
                    OLLAMA_MODEL,
                )
                if OLLAMA_FALLBACK_MODEL != OLLAMA_MODEL:
                    logger.warning("Falling back to %r", OLLAMA_FALLBACK_MODEL)
                    payload["model"] = OLLAMA_FALLBACK_MODEL
                    resp = client.post(url, json=payload)

            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except httpx.ConnectError as exc:
        logger.error("Cannot connect to Ollama at %s. Is it running? (ollama serve)", OLLAMA_BASE_URL)
        raise RuntimeError(f"Failed to call Ollama: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error in call_ollama_sync: %s", exc)
        raise RuntimeError(f"Failed to call Ollama: {exc}") from exc


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def check_ollama_health() -> dict[str, Any]:
    """Check Ollama availability and list available models.

    Returns:
        A dict with keys:
        - ``available`` (bool): Whether Ollama responded successfully.
        - ``models`` (list[str]): Names of available models (empty on failure).
    """
    import httpx

    try:
        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        models = [m["name"] for m in data.get("models", [])]
        return {"available": True, "models": models}
    except Exception as exc:
        logger.debug("Ollama health check failed: %s", exc)
        return {"available": False, "models": []}
