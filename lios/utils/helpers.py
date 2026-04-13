"""Shared utility helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


def sha256_hex(text: str) -> str:
    """Return the SHA-256 hex digest of *text*."""
    return hashlib.sha256(text.encode()).hexdigest()


def slugify(text: str) -> str:
    """Convert *text* to a lowercase, hyphenated slug suitable for IDs."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text


def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate *text* to *max_chars*, appending '…' if needed."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def flatten(nested: list[Any]) -> list[Any]:
    """Recursively flatten a nested list."""
    result: list[Any] = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
