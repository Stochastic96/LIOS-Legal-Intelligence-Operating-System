"""Abstract base class shared by all LIOS agents."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from lios.config import settings
from lios.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentResponse:
    agent_id: str
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0          # 0.0 – 1.0
    reasoning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Common interface for all LIOS analytical agents.

    Sub-classes implement ``_build_prompt`` and override ``agent_id``.
    The ``respond`` method handles LLM call routing (Ollama / OpenAI).
    """

    agent_id: str = "base"

    def __init__(self) -> None:
        self._logger = get_logger(f"lios.agents.{self.agent_id}")

    @abstractmethod
    async def respond(self, query: str, context_chunks: list[str]) -> AgentResponse:
        """Process *query* given *context_chunks* from the knowledge base."""

    # ── LLM helpers ───────────────────────────────────────────────────────────
    async def _call_llm(self, prompt: str) -> str:
        """Route LLM call to the configured provider."""
        if settings.llm_provider == "openai":
            return await self._call_openai(prompt)
        return await self._call_ollama(prompt)

    async def _call_ollama(self, prompt: str) -> str:
        import ollama  # lazy import

        self._logger.debug("Calling Ollama (%s)", settings.ollama_model)
        response = ollama.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]

    async def _call_openai(self, prompt: str) -> str:
        from openai import AsyncOpenAI  # lazy import

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._logger.debug("Calling OpenAI gpt-4o")
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return resp.choices[0].message.content or ""

    # ── Prompt utilities ──────────────────────────────────────────────────────
    @staticmethod
    def _format_context(chunks: list[str]) -> str:
        return "\n\n---\n\n".join(chunks)

    @staticmethod
    def _parse_json_response(raw: str) -> dict[str, Any]:
        """Extract JSON from a potentially markdown-wrapped LLM response."""
        raw = raw.strip()
        # Strip markdown code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}
