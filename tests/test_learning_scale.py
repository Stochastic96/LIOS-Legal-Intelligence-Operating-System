import json

from lios.memory import knowledge_map as km


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False))


def test_get_next_question_uses_pdf_corpus(tmp_path, monkeypatch):
    map_file = tmp_path / "knowledge_map.json"
    history_file = tmp_path / "answer_history.jsonl"
    corpus_file = tmp_path / "legal_chunks.jsonl"

    _write_json(
        map_file,
        [
            {
                "id": "csrd",
                "name": "CSRD",
                "category": "EU",
                "status": "learning",
                "pct": 20,
                "questions_asked": 0,
                "questions_answered": 0,
                "last_updated": None,
            }
        ],
    )
    corpus_file.write_text(
        json.dumps(
            {
                "regulation": "CSRD",
                "article": "Art.2",
                "title": "Definitions",
                "text": "Large undertaking thresholds and sustainability reporting obligations.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(km, "_MAP_FILE", map_file)
    monkeypatch.setattr(km, "_ANSWER_HISTORY_FILE", history_file)
    monkeypatch.setattr(km, "_CORPUS_FILE", corpus_file)
    monkeypatch.setattr(km, "_CORPUS_CHUNKS_CACHE", None)
    monkeypatch.setattr(km, "_SEED_MAP", [])

    q = km.get_next_question("csrd")
    assert q is not None
    assert q["type"] == "corpus"
    assert q["source"] == "pdf_corpus"
    assert "CSRD" in q["q"]
    assert "Art.2" in q["q"]


def test_get_next_learn_topic_include_mastered(tmp_path, monkeypatch):
    map_file = tmp_path / "knowledge_map.json"
    _write_json(
        map_file,
        [
            {
                "id": "a",
                "name": "A",
                "category": "EU",
                "status": "mastered",
                "pct": 95,
                "questions_asked": 4,
                "questions_answered": 4,
                "last_updated": None,
            },
            {
                "id": "b",
                "name": "B",
                "category": "EU",
                "status": "functional",
                "pct": 80,
                "questions_asked": 1,
                "questions_answered": 1,
                "last_updated": None,
            },
        ],
    )
    monkeypatch.setattr(km, "_MAP_FILE", map_file)
    monkeypatch.setattr(km, "_SEED_MAP", [])

    assert km.get_next_learn_topic() is None
    topic = km.get_next_learn_topic(include_mastered=True)
    assert topic is not None
    assert topic["id"] == "b"


def test_record_answer_uses_submitted_question_text(tmp_path, monkeypatch):
    map_file = tmp_path / "knowledge_map.json"
    history_file = tmp_path / "answer_history.jsonl"
    _write_json(
        map_file,
        [
            {
                "id": "csrd",
                "name": "CSRD",
                "category": "EU",
                "status": "seed",
                "pct": 10,
                "questions_asked": 0,
                "questions_answered": 0,
                "last_updated": None,
            }
        ],
    )
    monkeypatch.setattr(km, "_MAP_FILE", map_file)
    monkeypatch.setattr(km, "_ANSWER_HISTORY_FILE", history_file)
    monkeypatch.setattr(km, "_SEED_MAP", [])

    km.record_answer(
        topic_id="csrd",
        answer_text="Dies ist eine ausreichend lange Antwort für den Test.",
        reference="test",
        question_text="Welche Pflichten ergeben sich aus CSRD Art.2?",
    )

    lines = history_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["question"] == "Welche Pflichten ergeben sich aus CSRD Art.2?"
