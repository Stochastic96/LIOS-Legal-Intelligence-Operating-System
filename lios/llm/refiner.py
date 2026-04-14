"""Optional LLM answer refinement with Azure OpenAI and OpenAI-compatible backends."""

from __future__ import annotations

from typing import Any

from lios.config import settings
from lios.logging_setup import get_logger

logger = get_logger(__name__)


class LLMRefiner:
    """Refine rule-based answers with an optional chat model."""

    def __init__(self) -> None:
        self.enabled = settings.LLM_ENABLED

    def refine(self, query: str, draft_answer: str, context: dict[str, Any] | None = None) -> str:
        """Return a refined answer, or the original answer when LLM is unavailable."""
        if not self.enabled:
            return draft_answer

        try:
            if settings.LLM_PROVIDER.lower() == "azure":
                return self._refine_with_azure(query, draft_answer, context)
            return self._refine_openai_compatible(query, draft_answer, context)
        except Exception as exc:  # pragma: no cover - defensive fallback for external APIs
            logger.warning(f"LLM refinement failed, using rule-based answer: {exc}")
            return draft_answer

    def _system_prompt(self) -> str:
        return (
            "You are LIOS, a legal compliance co-pilot for EU sustainability regulations. "
            "Improve clarity and structure only. Do not invent legal citations. "
            "Keep legal meaning unchanged and preserve uncertainty when present."
        )

    def _build_messages(self, query: str, draft_answer: str, context: dict[str, Any] | None):
        ctx_line = ""
        if context:
            ctx_line = f"\nContext JSON: {context}"

        user_msg = (
            f"User query: {query}\n\n"
            f"Draft answer:\n{draft_answer}\n"
            f"{ctx_line}\n\n"
            "Rewrite this into a concise, well-structured answer with short headings. "
            "Do not add claims not present in the draft."
        )

        return [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": user_msg},
        ]

    def _refine_with_azure(self, query: str, draft_answer: str, context: dict[str, Any] | None) -> str:
        from openai import AzureOpenAI

        if not settings.AZURE_OPENAI_ENDPOINT:
            raise ValueError("LIOS_AZURE_OPENAI_ENDPOINT is required when provider is azure")
        if not settings.AZURE_OPENAI_API_KEY:
            raise ValueError("LIOS_AZURE_OPENAI_API_KEY is required when provider is azure")

        deployment = settings.AZURE_OPENAI_DEPLOYMENT or settings.LLM_MODEL
        if not deployment:
            raise ValueError("LIOS_AZURE_OPENAI_DEPLOYMENT or LIOS_LLM_MODEL must be set")

        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        response = client.chat.completions.create(
            model=deployment,
            messages=self._build_messages(query, draft_answer, context),
            temperature=0.2,
        )
        content = response.choices[0].message.content if response.choices else None
        return content.strip() if content else draft_answer

    def _refine_openai_compatible(
        self, query: str, draft_answer: str, context: dict[str, Any] | None
    ) -> str:
        from openai import OpenAI

        client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=self._build_messages(query, draft_answer, context),
            temperature=0.2,
        )
        content = response.choices[0].message.content if response.choices else None
        return content.strip() if content else draft_answer
