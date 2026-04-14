"""Tests for local chat training storage and direction inference."""

from __future__ import annotations

from pathlib import Path

from lios.features.chat_training import ChatTurn, LocalTrainingStore


def test_infer_session_direction_returns_hint_for_stable_intent(tmp_path: Path) -> None:
    store = LocalTrainingStore(tmp_path / "chat_training.jsonl")

    for i in range(3):
        store.append_turn(
            ChatTurn(
                timestamp=LocalTrainingStore.now_iso(),
                session_id="s1",
                user_query=f"What is CSRD? {i}",
                answer="CSRD summary",
                intent="legal_breakdown",
                citations=[
                    {
                        "regulation": "CSRD",
                        "article_id": "Art.1",
                        "title": "Subject matter and scope",
                        "relevance_score": 10,
                    }
                ],
                metadata={},
            )
        )

    hint = store.infer_session_direction("s1", window=3)
    assert hint is not None
    assert hint["intent"] == "legal_breakdown"
    assert hint["regulation"] == "CSRD"


def test_infer_session_direction_none_when_not_enough_turns(tmp_path: Path) -> None:
    store = LocalTrainingStore(tmp_path / "chat_training.jsonl")
    store.append_turn(
        ChatTurn(
            timestamp=LocalTrainingStore.now_iso(),
            session_id="s2",
            user_query="What is CSRD?",
            answer="CSRD summary",
            intent="legal_breakdown",
            citations=[],
            metadata={},
        )
    )

    hint = store.infer_session_direction("s2", window=3)
    assert hint is None
