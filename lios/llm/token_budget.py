"""Token budget and usage tracking for LLM calls.

Keeps Azure costs predictable by:
- Mapping query intent → max_tokens limit
- Logging every LLM call to logs/token_usage.jsonl
- Providing a running cost estimate (gpt-4o-mini pricing)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lios.config import settings
from lios.logging_setup import get_logger

logger = get_logger(__name__)

# gpt-4o-mini pricing (USD per 1M tokens) — update if pricing changes
_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini":    {"input": 0.15,  "output": 0.60},
    "gpt-4o":         {"input": 5.00,  "output": 15.00},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    "llama-3.3-70b-versatile": {"input": 0.0,  "output": 0.0},   # Groq free tier
    "mistral:latest":  {"input": 0.0,  "output": 0.0},            # local Ollama
}

# Intent → max_tokens mapping
_INTENT_BUDGETS: dict[str, int] = {
    "definition":        settings.TOKEN_BUDGET_DEFINITION,
    "general_query":     settings.TOKEN_BUDGET_DEFAULT,
    "general_law":       settings.TOKEN_BUDGET_GENERAL_LAW,
    "applicability":     settings.TOKEN_BUDGET_APPLICABILITY,
    "compliance_roadmap": settings.TOKEN_BUDGET_ROADMAP,
    "legal_breakdown":   settings.TOKEN_BUDGET_BREAKDOWN,
    "conflict_detection": settings.TOKEN_BUDGET_BREAKDOWN,
}


def max_tokens_for_intent(intent: str | None) -> int:
    """Return the max_tokens budget for a given query intent."""
    if not intent:
        return settings.TOKEN_BUDGET_DEFAULT
    return _INTENT_BUDGETS.get(intent.lower(), settings.TOKEN_BUDGET_DEFAULT)


def log_usage(
    provider: str,
    model: str,
    intent: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    query_preview: str = "",
) -> None:
    """Append a token usage entry to the token log file."""
    total = prompt_tokens + completion_tokens
    price = _PRICING.get(model, {"input": 0.0, "output": 0.0})
    cost_usd = (prompt_tokens * price["input"] + completion_tokens * price["output"]) / 1_000_000

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "intent": intent or "unknown",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "cost_usd": round(cost_usd, 6),
        "query": query_preview[:80],
    }

    log_path = Path(settings.TOKEN_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    logger.info(
        "Token usage | model=%s intent=%s in=%d out=%d cost=$%.4f",
        model, intent or "?", prompt_tokens, completion_tokens, cost_usd,
    )


def usage_summary() -> dict[str, Any]:
    """Read the token log and return a cost summary."""
    log_path = Path(settings.TOKEN_LOG_PATH)
    if not log_path.exists():
        return {"total_calls": 0, "total_tokens": 0, "total_cost_usd": 0.0, "by_model": {}}

    total_calls = 0
    total_tokens = 0
    total_cost = 0.0
    by_model: dict[str, dict[str, Any]] = {}

    for line in log_path.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            total_calls += 1
            total_tokens += e.get("total_tokens", 0)
            total_cost += e.get("cost_usd", 0.0)
            m = e.get("model", "unknown")
            if m not in by_model:
                by_model[m] = {"calls": 0, "tokens": 0, "cost_usd": 0.0}
            by_model[m]["calls"] += 1
            by_model[m]["tokens"] += e.get("total_tokens", 0)
            by_model[m]["cost_usd"] = round(by_model[m]["cost_usd"] + e.get("cost_usd", 0.0), 6)
        except Exception:
            continue

    return {
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "by_model": by_model,
    }
