"""Brain state manager — runtime toggle for Ollama without server restart."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

import httpx

_STATE_FILE = Path("data/memory/brain_state.json")
_lock = Lock()

_DEFAULTS = {
    "enabled": True,
    "model": os.environ.get("LIOS_LLM_MODEL", "mistral"),
    "base_url": os.environ.get("LIOS_LLM_BASE_URL", "http://localhost:11434"),
    "toggled_at": None,
}


def _load() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save(state: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def get_state() -> dict:
    with _lock:
        return _load()


def set_enabled(enabled: bool) -> dict:
    with _lock:
        state = _load()
        state["enabled"] = enabled
        state["toggled_at"] = datetime.now(timezone.utc).isoformat()
        _save(state)
        return state


def is_enabled() -> bool:
    return _load().get("enabled", True)


def check_llm_reachable() -> bool:
    base_url = _load().get("base_url", _DEFAULTS["base_url"])
    try:
        resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=3.0)
        return resp.status_code < 500
    except Exception:
        return False


def get_knowledge_chunk_count() -> int:
    try:
        from lios.retrieval.chroma_retriever import total_chunks
        count = total_chunks()
        if count > 0:
            return count
    except Exception:
        pass
    corpus = Path("data/corpus/legal_chunks.jsonl")
    if not corpus.exists():
        return 0
    return sum(1 for line in corpus.read_text().splitlines() if line.strip())


def get_model() -> str:
    return _load().get("model", _DEFAULTS["model"])


def get_base_url() -> str:
    return _load().get("base_url", _DEFAULTS["base_url"])
