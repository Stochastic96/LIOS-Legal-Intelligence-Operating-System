"""Optional LLM answer refinement — supports Ollama/OpenAI-compatible and Azure OpenAI backends."""

from __future__ import annotations

import json
from typing import Any

import httpx

from lios.config import settings
from lios.logging_setup import get_logger

logger = get_logger(__name__)

# Static system prompt — kept as module-level constant so every call uses
# identical instructions (important for answer consistency).
_SYSTEM_PROMPT = (
    "You are LIOS — a specialist EU sustainability regulation compliance advisor.\n"
    "Your expertise covers: CSRD, ESRS standards, EU Taxonomy Regulation, SFDR, CS3D, "
    "EU Deforestation Regulation (EUDR), and related ESG disclosure frameworks.\n\n"

    "## Your primary job\n"
    "You receive a user compliance question and a structured draft that contains:\n"
    "  1. Retrieved legal provisions (exact article texts from the regulatory database)\n"
    "  2. Expert compliance analysis (pre-built rule-based knowledge)\n"
    "Your job is to synthesise these into one clear, accurate, cited compliance answer.\n\n"

    "## Output format\n"
    "- Open with a direct answer to the question in 1–2 sentences — no preamble\n"
    "- Use ## headings for structure: ## Applicability, ## Key Obligations, "
    "## Thresholds, ## Deadlines, ## Penalties, ## Key Actions\n"
    "- Cite specific legal references whenever they appear in the draft "
    "(e.g. CSRD Art.19a, ESRS E1 §34, SFDR Art.8, EU Taxonomy Art.3(1)(c))\n"
    "- Use bullet points for lists of obligations, thresholds, dates, or steps\n"
    "- End with **## Key Actions** when the question requires compliance steps\n\n"

    "## Accuracy and legal integrity rules\n"
    "- ONLY use facts, numbers, thresholds, dates, and citations present in the draft\n"
    "- Do NOT invent or extrapolate any regulatory detail not in the draft\n"
    "- Preserve legal uncertainty exactly as stated — keep phrases like "
    "'subject to interpretation', 'may apply', 'consult legal counsel'\n"
    "- Clearly distinguish mandatory obligations (shall/must) from guidance (should/recommended)\n"
    "- For phased regulations (CSRD, CS3D), always state which phase and timeline applies\n"
    "- If the draft says 'insufficient data', say so and direct to official sources\n\n"

    "## Tone and audience\n"
    "- Authoritative but accessible — target audience is compliance officers and legal counsel\n"
    "- Specific and actionable: give exact thresholds, dates, and article references\n"
    "- Concise: aim for 200–400 words for a typical query; longer only for roadmap/breakdown queries\n"
    "- Never list 'agents' or 'perspectives' — output one unified answer\n"
    "- Do not explain what you are doing — just answer the question"
)


class LLMRefiner:
    """Refine rule-based answers with a local Ollama/Mistral model (or Azure OpenAI)."""

    def __init__(self) -> None:
        self.enabled = settings.LLM_ENABLED

    def refine(self, query: str, draft_answer: str, context: dict[str, Any] | None = None) -> str:
        """Return a refined answer, or the original draft when LLM is unavailable."""
        if not self.enabled:
            return draft_answer

        try:
            if settings.LLM_PROVIDER.lower() == "azure":
                return self._refine_with_azure(query, draft_answer, context)
            return self._refine_openai_compatible(query, draft_answer, context)
        except Exception as exc:
            logger.warning(f"LLM refinement failed, using rule-based answer: {exc}")
            return draft_answer

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def _build_messages(self, query: str, draft_answer: str, context: dict[str, Any] | None):
        rag_context = context.get("rag_context", "") if context else ""
        rag_section = f"\nRetrieved legal context:\n{rag_context}\n" if rag_context else ""

        extra = {k: v for k, v in context.items() if k != "rag_context"} if context else {}
        ctx_line = f"\nContext JSON: {extra}" if extra else ""

        user_msg = (
            f"User query: {query}\n"
            f"{rag_section}"
            f"\nDraft answer:\n{draft_answer}\n"
            f"{ctx_line}\n\n"
            "Rewrite this into a concise, well-structured answer with short headings. "
            "Do not add claims not present in the draft or retrieved context."
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
            messages=[{"role": "system", "content": _SYSTEM_PROMPT}]
            + self._build_messages(query, draft_answer, context),
            temperature=0.2,
        )
        content = response.choices[0].message.content if response.choices else None
        return content.strip() if content else draft_answer

    def _refine_openai_compatible(
        self, query: str, draft_answer: str, context: dict[str, Any] | None
    ) -> str:
        """Calls any OpenAI-compatible endpoint — Ollama, LM Studio, vLLM, etc."""
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [{"role": "system", "content": _SYSTEM_PROMPT}]
            + self._build_messages(query, draft_answer, context),
            "temperature": 0.2,
        }

        base_url = settings.LLM_BASE_URL.rstrip("/")
        endpoint = f"{base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if settings.LLM_API_KEY:
            headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

        with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        content = None
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            content = None

        return content.strip() if isinstance(content, str) and content.strip() else draft_answer

    # ------------------------------------------------------------------
    # Shared message builder
    # ------------------------------------------------------------------

    def _build_messages(
        self, query: str, draft_answer: str, context: dict[str, Any] | None
    ) -> list[dict[str, str]]:
        ctx_parts: list[str] = []
        if context:
            if context.get("intent"):
                ctx_parts.append(f"Query intent: {context['intent']}")
            if context.get("regulations"):
                ctx_parts.append(f"Regulations identified: {', '.join(context['regulations'])}")
            if context.get("company_profile"):
                ctx_parts.append(f"Company profile: {context['company_profile']}")
        ctx_block = ("\n\n**Context:**\n" + "\n".join(ctx_parts)) if ctx_parts else ""

        user_msg = (
            f"**Compliance question:** {query}"
            f"{ctx_block}\n\n"
            f"**Draft (retrieved legal provisions + expert analysis):**\n{draft_answer}\n\n"
            "Write a clear, accurate, well-structured compliance answer based strictly "
            "on the draft above. Cite article references where available. "
            "Do not add any facts, numbers, or dates not present in the draft."
        )
        return [{"role": "user", "content": user_msg}]
