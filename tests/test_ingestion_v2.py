"""Tests for V2 seed corpus builder."""

from __future__ import annotations

from pathlib import Path

from lios.ingestion.build_seed_corpus import build_seed_corpus


def test_build_seed_corpus_writes_jsonl(tmp_path: Path) -> None:
    out = tmp_path / "legal_chunks.jsonl"
    count = build_seed_corpus(out)
    assert count > 0
    assert out.exists()
    assert out.read_text(encoding="utf-8").strip()
