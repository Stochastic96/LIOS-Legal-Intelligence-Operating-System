"""Intelligence API — real-time corpus and learning KPIs for the mobile Intelligenz screen."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

_CORPUS_FILE         = Path("data/corpus/legal_chunks.jsonl")
_MAP_FILE            = Path("data/memory/knowledge_map.json")
_ANSWER_HISTORY_FILE = Path("data/memory/answer_history.jsonl")
_CORRECTIONS_FILE    = Path("data/memory/corrections.json")

TARGET_CHUNKS    = 87_000
TARGET_QUESTIONS = 1_000_000


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def _load_chunks() -> list[dict]:
    return _read_jsonl(_CORPUS_FILE)


def _load_answers() -> list[dict]:
    return _read_jsonl(_ANSWER_HISTORY_FILE)


# ── Question bank size (imported lazily to avoid circular imports) ─────────────

def _total_questions_in_bank() -> int:
    try:
        from lios.memory.knowledge_map import _QUESTION_BANK
        return sum(len(v) for v in _QUESTION_BANK.values())
    except Exception:
        return 0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/stats")
def intelligence_stats() -> dict[str, Any]:
    """Top-level KPIs: chunks, regulations, topics, questions, answer velocity."""
    chunks      = _load_chunks()
    topics      = _read_json(_MAP_FILE, [])
    answers     = _load_answers()
    corrections = _read_json(_CORRECTIONS_FILE, [])

    regs = {c.get("regulation", "") for c in chunks if c.get("regulation")}
    total_q = _total_questions_in_bank()

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    answers_7d = sum(
        1 for a in answers
        if a.get("ts") and datetime.fromisoformat(a["ts"].replace("Z", "+00:00")) >= week_ago
    )
    valid_answers = sum(1 for a in answers if a.get("valid"))
    functional_or_mastered = sum(
        1 for t in topics if t.get("status") in ("functional", "mastered")
    )
    overall_pct = (
        round(sum(t["pct"] for t in topics) / len(topics)) if topics else 0
    )
    corpus_pct = round(len(chunks) / TARGET_CHUNKS * 100, 1) if TARGET_CHUNKS else 0

    return {
        "total_chunks":                  len(chunks),
        "total_regulations":             len(regs),
        "total_official_docs":           len(regs),
        "total_topics":                  len(topics),
        "total_questions_in_bank":       total_q,
        "total_answers_submitted":       len(answers),
        "valid_answers":                 valid_answers,
        "topics_functional_or_mastered": functional_or_mastered,
        "overall_learning_pct":          overall_pct,
        "corrections_count":             len(corrections),
        "answers_last_7_days":           answers_7d,
        "target_chunks":                 TARGET_CHUNKS,
        "target_questions":              TARGET_QUESTIONS,
        "corpus_completeness_pct":       corpus_pct,
    }


@router.get("/corpus")
def intelligence_corpus() -> list[dict[str, Any]]:
    """Per-regulation breakdown from the corpus, sorted by chunk count."""
    chunks = _load_chunks()
    by_reg: dict[str, list[dict]] = defaultdict(list)
    for c in chunks:
        by_reg[c.get("regulation", "UNKNOWN")].append(c)

    rows = []
    for reg, chs in by_reg.items():
        sample = chs[0]
        articles = sorted({c.get("article", "") for c in chs if c.get("article")})
        rows.append({
            "regulation":   reg,
            "celex_id":     sample.get("celex_or_doc_id", ""),
            "jurisdiction": sample.get("jurisdiction", "EU"),
            "chunk_count":  len(chs),
            "article_count": len(articles),
            "articles":     articles[:20],
            "source_url":   sample.get("source_url", ""),
            "last_indexed": sample.get("ingestion_timestamp", ""),
            "published_date": sample.get("published_date", ""),
        })

    rows.sort(key=lambda r: -r["chunk_count"])
    return rows


@router.get("/topics")
def intelligence_topics() -> list[dict[str, Any]]:
    """Per-topic view: learning progress + corpus chunk count."""
    topics  = _read_json(_MAP_FILE, [])
    chunks  = _load_chunks()
    answers = _load_answers()

    try:
        from lios.memory.knowledge_map import _QUESTION_BANK
        qbank = _QUESTION_BANK
    except Exception:
        qbank = {}

    # Build chunk count per regulation key
    chunks_by_reg: dict[str, int] = defaultdict(int)
    for c in chunks:
        reg = c.get("regulation", "").upper()
        chunks_by_reg[reg] += 1

    # Build answer stats per topic
    ans_by_topic: dict[str, int] = defaultdict(int)
    for a in answers:
        ans_by_topic[a.get("topic_id", "")] += 1

    # Map topic IDs to regulation keys (best-effort fuzzy match)
    _reg_map = {
        "csrd": "CSRD", "esrs": "ESRS", "eu_taxonomy": "EU_TAXONOMY",
        "sfdr": "SFDR", "cs3d": "CS3D", "csddd": "CSDDD",
        "gdpr": "GDPR", "lksg": "LKSG", "hgb": "HGB",
        "german_corporate": "AKTG", "ai_act": "AI_ACT", "nis2": "NIS2",
        "behg": "BEHG", "ksg": "KSG", "reach": "REACH",
        "eu_whistleblower": "WHISTLEBLOWER", "eu_competition": "EU_COMPETITION",
        "gri": "GRI", "tcfd": "TCFD", "issb": "ISSB",
        "greenwashing_law": "EU_GREENWASHING", "mifid2": "MIFID2",
        "teu": "TEU", "tfeu": "AEUV", "eu_charter": "EU_CHARTER",
        "srd2": "SRD2", "ied": "IED", "dora": "DORA", "cbam": "CBAM",
    }

    rows = []
    for t in topics:
        tid   = t["id"]
        reg   = _reg_map.get(tid, tid.upper())
        ccount = chunks_by_reg.get(reg, 0)
        rows.append({
            "id":                  tid,
            "name":                t["name"],
            "category":            t.get("category", ""),
            "status":              t.get("status", "unknown"),
            "pct":                 t.get("pct", 0),
            "questions_in_bank":   len(qbank.get(tid, [])),
            "questions_asked":     t.get("questions_asked", 0),
            "questions_answered":  t.get("questions_answered", 0),
            "last_activity":       t.get("last_updated"),
            "has_corpus_chunks":   ccount > 0,
            "corpus_chunk_count":  ccount,
        })

    rows.sort(key=lambda r: (-r["pct"], r["name"]))
    return rows


@router.get("/answers")
def intelligence_answers(limit: int = 20) -> dict[str, Any]:
    """Recent answer history with a corpus hint per question."""
    answers = _load_answers()
    answers = list(reversed(answers))[:limit]

    chunks = _load_chunks()
    # Build a lightweight text-search index: list of (text_lower, chunk)
    _idx = [(c.get("text", "").lower(), c) for c in chunks if c.get("text")]

    def _corpus_hint(question: str) -> str:
        if not question or not _idx:
            return ""
        words = [w for w in question.lower().split() if len(w) > 4]
        if not words:
            return ""
        best_chunk = ""
        best_score = 0
        for text_lower, chunk in _idx:
            score = sum(1 for w in words if w in text_lower)
            if score > best_score:
                best_score = score
                best_chunk = chunk.get("text", "")[:300]
        return best_chunk if best_score > 0 else ""

    enriched = []
    for a in answers:
        hint = _corpus_hint(a.get("question", ""))
        enriched.append({
            "id":          a.get("id", ""),
            "ts":          a.get("ts", ""),
            "topic_name":  a.get("topic_name", ""),
            "category":    a.get("category", ""),
            "question":    a.get("question", ""),
            "user_answer": a.get("user_answer", ""),
            "reference":   a.get("reference", ""),
            "pct_before":  a.get("pct_before", 0),
            "pct_after":   a.get("pct_after", 0),
            "valid":       a.get("valid", False),
            "corpus_hint": hint,
        })

    return {"answers": enriched, "total": len(_read_jsonl(_ANSWER_HISTORY_FILE))}
