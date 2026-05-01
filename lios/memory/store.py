"""Persistent memory store — corrections, rules, feedback, verified answers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

_MEMORY_DIR = Path("data/memory")
_CORRECTIONS_FILE = _MEMORY_DIR / "corrections.json"
_RULES_FILE = _MEMORY_DIR / "rules.json"
_lock = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── Corrections ──────────────────────────────────────────────────────────────

def add_correction(
    session_id: str,
    user_query: str,
    original_answer: str,
    feedback_type: str,          # "wrong" | "partial"
    correction_text: str,
    make_rule: bool = False,
) -> dict:
    with _lock:
        corrections = _load_json(_CORRECTIONS_FILE, [])
        entry: dict = {
            "id": f"corr-{len(corrections) + 1:04d}",
            "created_at": _now(),
            "session_id": session_id,
            "user_query": user_query,
            "original_answer": original_answer,
            "feedback_type": feedback_type,
            "correction_text": correction_text,
            "made_rule": make_rule,
        }
        corrections.append(entry)
        _save_json(_CORRECTIONS_FILE, corrections)

        if make_rule:
            _add_rule_internal(
                corrections,
                source="correction",
                rule_text=correction_text,
                topic=_infer_topic(user_query),
            )

        return entry


def list_corrections(limit: int = 50) -> list[dict]:
    with _lock:
        corrections = _load_json(_CORRECTIONS_FILE, [])
        return list(reversed(corrections))[:limit]


# ── Rules ─────────────────────────────────────────────────────────────────────

def _add_rule_internal(existing_corrections: list, source: str, rule_text: str, topic: str) -> dict:
    rules = _load_json(_RULES_FILE, [])
    rule: dict = {
        "id": f"rule-{len(rules) + 1:04d}",
        "created_at": _now(),
        "source": source,
        "topic": topic,
        "rule_text": rule_text,
        "active": True,
    }
    rules.append(rule)
    _save_json(_RULES_FILE, rules)
    return rule


def add_rule(rule_text: str, topic: str = "general", source: str = "user") -> dict:
    with _lock:
        return _add_rule_internal([], source=source, rule_text=rule_text, topic=topic)


def list_rules(active_only: bool = True) -> list[dict]:
    with _lock:
        rules = _load_json(_RULES_FILE, [])
        if active_only:
            return [r for r in rules if r.get("active", True)]
        return rules


def deactivate_rule(rule_id: str) -> bool:
    with _lock:
        rules = _load_json(_RULES_FILE, [])
        for rule in rules:
            if rule["id"] == rule_id:
                rule["active"] = False
                _save_json(_RULES_FILE, rules)
                return True
        return False


def get_active_rules_as_prompt_block() -> str:
    """Return active rules formatted for injection into LLM system prompt."""
    rules = list_rules(active_only=True)
    if not rules:
        return ""
    lines = ["## Permanent rules (always follow these)"]
    for r in rules:
        lines.append(f"- {r['rule_text']}")
    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_topic(query: str) -> str:
    query_lower = query.lower()
    topics = {
        "csrd": "CSRD",
        "esrs": "ESRS",
        "taxonomy": "EU Taxonomy",
        "sfdr": "SFDR",
        "tcfd": "TCFD",
        "issb": "ISSB",
        "greenwash": "Greenwashing",
        "carbon": "Carbon",
        "esg": "ESG",
        "gri": "GRI",
    }
    for keyword, topic in topics.items():
        if keyword in query_lower:
            return topic
    return "general"
