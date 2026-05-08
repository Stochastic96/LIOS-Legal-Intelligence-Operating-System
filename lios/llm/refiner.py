"""Optional LLM answer refinement — supports Ollama/OpenAI-compatible and Azure OpenAI backends."""

from __future__ import annotations

import json
from typing import Any

import httpx

from lios.config import settings
from lios.logging_setup import get_logger

logger = get_logger(__name__)

# Full system prompt — used for Ollama/Groq where tokens are free.
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

# Compact system prompt — used for Azure OpenAI to minimise input tokens.
# ~60% shorter than the full prompt while preserving all critical instructions.
_SYSTEM_PROMPT_COMPACT = (
    "You are LIOS, EU sustainability regulation advisor (CSRD, ESRS, EU Taxonomy, SFDR, CS3D, EUDR).\n"
    "Synthesise the retrieved legal provisions and draft into ONE clear, cited compliance answer.\n"
    "Rules: open with a direct 1-2 sentence answer; use ## headings (Applicability/Obligations/"
    "Thresholds/Deadlines/Key Actions); cite article refs (e.g. CSRD Art.19a); bullets for lists.\n"
    "Accuracy: only use facts/dates/thresholds in the draft; never invent citations; "
    "flag legal uncertainty; distinguish shall vs should; state CSRD/CS3D phase.\n"
    "Audience: compliance officers. Concise: 150-400 words. No meta-commentary."
)


# Runtime override — set by /api/llm-mode endpoint without restarting the server.
# Keys: "provider" ("local" | "groq" | "azure"), "model", "base_url", "api_key"
_RUNTIME_CONFIG: dict[str, str] = {}


def set_runtime_provider(provider: str, model: str = "", base_url: str = "", api_key: str = "") -> None:
    """Switch the active LLM provider at runtime without a server restart."""
    _RUNTIME_CONFIG["provider"] = provider
    if model:
        _RUNTIME_CONFIG["model"] = model
    if base_url:
        _RUNTIME_CONFIG["base_url"] = base_url
    if api_key:
        _RUNTIME_CONFIG["api_key"] = api_key
    logger.info("Runtime LLM provider switched to: %s", provider)


def get_runtime_provider() -> str:
    """Return the active provider name (runtime override or env default)."""
    return _RUNTIME_CONFIG.get("provider", settings.LLM_PROVIDER.lower())


class LLMRefiner:
    """Refine rule-based answers with a local Ollama/Mistral model (or Azure OpenAI)."""

    def __init__(self) -> None:
        self.enabled = settings.LLM_ENABLED

    def refine(
        self,
        query: str,
        draft_answer: str,
        context: dict[str, Any] | None = None,
        intent: str | None = None,
    ) -> str:
        """Return a refined answer, or the original draft when LLM is unavailable."""
        if not self.enabled:
            return draft_answer

        try:
            provider = get_runtime_provider()
            if provider == "azure":
                return self._refine_with_azure(query, draft_answer, context, intent=intent)
            return self._refine_openai_compatible(query, draft_answer, context, intent=intent)
        except Exception as exc:
            logger.warning(f"LLM refinement failed, using rule-based answer: {exc}")
            return draft_answer

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def _refine_with_azure(
        self,
        query: str,
        draft_answer: str,
        context: dict[str, Any] | None,
        intent: str | None = None,
    ) -> str:
        from openai import AzureOpenAI
        from lios.llm.token_budget import log_usage, max_tokens_for_intent

        if not settings.AZURE_OPENAI_ENDPOINT:
            raise ValueError("LIOS_AZURE_OPENAI_ENDPOINT is required when provider is azure")
        if not settings.AZURE_OPENAI_API_KEY:
            raise ValueError("LIOS_AZURE_OPENAI_API_KEY is required when provider is azure")

        deployment = (
            _RUNTIME_CONFIG.get("model")
            or settings.AZURE_OPENAI_DEPLOYMENT
            or settings.LLM_MODEL
        )
        if not deployment:
            raise ValueError("LIOS_AZURE_OPENAI_DEPLOYMENT or LIOS_LLM_MODEL must be set")

        max_tok = max_tokens_for_intent(intent)

        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT_COMPACT}]
            + self._build_messages(query, draft_answer, context),
            temperature=0.2,
            max_tokens=max_tok,
            seed=42,
        )

        # Log token usage for cost tracking
        usage = response.usage
        if usage:
            log_usage(
                provider="azure",
                model=deployment,
                intent=intent,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                query_preview=query,
            )

        content = response.choices[0].message.content if response.choices else None
        return content.strip() if content else draft_answer

    def _refine_openai_compatible(
        self,
        query: str,
        draft_answer: str,
        context: dict[str, Any] | None,
        intent: str | None = None,
    ) -> str:
        """Calls any OpenAI-compatible endpoint — Ollama, Groq, LM Studio, vLLM, etc."""
        from lios.llm.token_budget import log_usage, max_tokens_for_intent

        model = _RUNTIME_CONFIG.get("model", settings.LLM_MODEL)
        base_url = _RUNTIME_CONFIG.get("base_url", settings.LLM_BASE_URL).rstrip("/")
        api_key = _RUNTIME_CONFIG.get("api_key", settings.LLM_API_KEY)
        max_tok = max_tokens_for_intent(intent)

        payload = {
            "model": model,
            "messages": [{"role": "system", "content": _SYSTEM_PROMPT}]
            + self._build_messages(query, draft_answer, context),
            "temperature": 0.2,
            "max_tokens": max_tok,
        }

        endpoint = f"{base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        content = None
        try:
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            if usage.get("prompt_tokens"):
                log_usage(
                    provider=get_runtime_provider(),
                    model=model,
                    intent=intent,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    query_preview=query,
                )
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            content = None

        return content.strip() if isinstance(content, str) and content.strip() else draft_answer

    # ------------------------------------------------------------------
    # Message builder
    # ------------------------------------------------------------------

    def _build_messages(
        self, query: str, draft_answer: str, context: dict[str, Any] | None
    ) -> list[dict[str, str]]:
        ctx_parts: list[str] = []
        rag_context = ""
        if context:
            if context.get("intent"):
                ctx_parts.append(f"Query intent: {context['intent']}")
            if context.get("regulations"):
                ctx_parts.append(f"Regulations identified: {', '.join(context['regulations'])}")
            if context.get("company_profile"):
                ctx_parts.append(f"Company profile: {context['company_profile']}")
            rag_context = context.get("rag_context", "")

        ctx_block = ("\n\n**Context:**\n" + "\n".join(ctx_parts)) if ctx_parts else ""
        rag_block = (
            f"\n\n**Retrieved legal provisions:**\n{rag_context}"
            if rag_context else ""
        )

        user_msg = (
            f"**Compliance question:** {query}"
            f"{ctx_block}"
            f"{rag_block}\n\n"
            f"**Draft answer (rule-based analysis):**\n{draft_answer}\n\n"
            "Synthesise the retrieved legal provisions and the draft into one clear, "
            "well-structured compliance answer. Use the ## headings from the system prompt. "
            "Cite article references where they appear. "
            "Do not add any facts, numbers, or dates not present in the draft or retrieved context."
        )
        return [{"role": "user", "content": user_msg}]
