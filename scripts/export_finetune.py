#!/usr/bin/env python3
"""Export fine-tuning data in Mistral chat format.

Reads two sources:
  1. ``data/memory/corrections.json`` — user corrections (highest signal)
  2. ``logs/chat_training.jsonl``    — approved chat history pairs

Outputs ``data/training/finetune_export_{date}.jsonl`` where each line is:
  ``{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}``

Usage::

    python scripts/export_finetune.py
    python scripts/export_finetune.py --no-chat         # corrections only
    python scripts/export_finetune.py --output /tmp/ft.jsonl
    python scripts/export_finetune.py --min-answer-len 200
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_CORRECTIONS_PATH = _ROOT / "data" / "memory" / "corrections.json"
_CHAT_LOG_PATH = _ROOT / "logs" / "chat_training.jsonl"
_OUTPUT_DIR = _ROOT / "data" / "training"

# Patterns that indicate a low-quality/error answer from the chat log
_BAD_ANSWER_PREFIXES = (
    "I don't have",
    "I'm not able",
    "I cannot",
    "Error",
    "Sorry",
    "_(Brain is off",
)

# Minimum character length for a usable answer
_DEFAULT_MIN_ANSWER_LEN = 150
_MIN_CORRECTION_LEN = 80

# Learn-mode queries are synthetic — exclude from chat pairs
_LEARN_PREFIX = "[LEARN]"


def export_finetune(
    corrections_path: Path = _CORRECTIONS_PATH,
    chat_log_path: Path = _CHAT_LOG_PATH,
    output_path: Path | None = None,
    include_chat: bool = True,
    min_answer_len: int = _DEFAULT_MIN_ANSWER_LEN,
) -> tuple[int, int]:
    """Build and write the fine-tuning export.

    Args:
        corrections_path: Path to corrections.json.
        chat_log_path: Path to chat_training.jsonl.
        output_path: Destination JSONL file. Auto-named by date if None.
        include_chat: Include chat_training.jsonl pairs alongside corrections.
        min_answer_len: Minimum answer character length for chat pairs.

    Returns:
        ``(corrections_count, chat_count)`` — number of pairs from each source.
    """
    if output_path is None:
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = _OUTPUT_DIR / f"finetune_export_{date.today()}.jsonl"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    seen_queries: set[str] = set()
    records: list[dict] = []

    # ── Source 1: corrections (highest training signal) ──────────────────────
    corrections_count = 0
    corr_pairs = _load_corrections(corrections_path)
    for user_msg, assistant_msg in corr_pairs:
        key = user_msg.strip().lower()
        if key in seen_queries:
            continue
        seen_queries.add(key)
        records.append(_make_record(user_msg, assistant_msg))
        corrections_count += 1

    # ── Source 2: approved chat history ──────────────────────────────────────
    chat_count = 0
    if include_chat:
        chat_pairs = _load_chat_pairs(chat_log_path, min_answer_len)
        for user_msg, assistant_msg in chat_pairs:
            key = user_msg.strip().lower()
            if key in seen_queries:
                continue
            seen_queries.add(key)
            records.append(_make_record(user_msg, assistant_msg))
            chat_count += 1

    with output_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return corrections_count, chat_count


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def _load_corrections(path: Path) -> list[tuple[str, str]]:
    """Read corrections.json and yield (user_query, correction_text) pairs."""
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []

    pairs: list[tuple[str, str]] = []
    for entry in data:
        query = (entry.get("user_query") or "").strip()
        correction = (entry.get("correction_text") or "").strip()
        if not query or not correction:
            continue
        # Skip learn-mode entries (system-generated, not real user queries)
        if query.startswith(_LEARN_PREFIX):
            continue
        # Short corrections are feedback labels, not usable training answers
        if len(correction) < _MIN_CORRECTION_LEN:
            continue
        pairs.append((query, correction))

    return pairs


def _load_chat_pairs(path: Path, min_len: int) -> list[tuple[str, str]]:
    """Read chat_training.jsonl and yield high-quality (query, answer) pairs."""
    if not path.exists():
        return []

    pairs: list[tuple[str, str]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            query = (entry.get("user_query") or "").strip()
            answer = (entry.get("answer") or "").strip()

            if not query or not answer:
                continue
            if len(answer) < min_len:
                continue
            if any(answer.startswith(p) for p in _BAD_ANSWER_PREFIXES):
                continue

            pairs.append((query, answer))

    return pairs


def _make_record(user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export LIOS corrections + chat history as Mistral fine-tuning JSONL."
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Output JSONL path. Default: data/training/finetune_export_{date}.jsonl",
    )
    parser.add_argument(
        "--no-chat",
        action="store_true",
        help="Exclude chat_training.jsonl; output corrections only.",
    )
    parser.add_argument(
        "--min-answer-len",
        type=int,
        default=_DEFAULT_MIN_ANSWER_LEN,
        metavar="N",
        help=f"Minimum answer length for chat pairs. Default: {_DEFAULT_MIN_ANSWER_LEN}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    output_path = Path(args.output) if args.output else None

    corr_count, chat_count = export_finetune(
        include_chat=not args.no_chat,
        output_path=output_path,
        min_answer_len=args.min_answer_len,
    )

    effective_path = output_path or (
        _OUTPUT_DIR / f"finetune_export_{date.today()}.jsonl"
    )
    total = corr_count + chat_count
    print(f"Exported {total} pairs ({corr_count} corrections, {chat_count} chat)")
    print(f"Output: {effective_path}")


if __name__ == "__main__":
    main()
