"""ChromaDB-backed semantic retriever for LIOS.

Falls back to keyword search on legal_chunks.jsonl if ChromaDB is empty or
sentence-transformers is not installed.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_VECTORDB_PATH = str(Path("data/vectordb").resolve())
_CORPUS_FILE = Path("data/corpus/legal_chunks.jsonl")
_EMBED_MODEL = "all-MiniLM-L6-v2"

_lock = threading.Lock()
_client = None
_ef = None  # embedding function


def _get_client():
    global _client, _ef
    if _client is not None:
        return _client, _ef
    with _lock:
        if _client is not None:
            return _client, _ef
        try:
            import chromadb
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            Path(_VECTORDB_PATH).mkdir(parents=True, exist_ok=True)
            _client = chromadb.PersistentClient(path=_VECTORDB_PATH)
            _ef = SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)
        except ImportError:
            _client = None
            _ef = None
    return _client, _ef


def _get_collection(name: str):
    client, ef = _get_client()
    if client is None:
        return None
    try:
        return client.get_or_create_collection(name=name, embedding_function=ef)
    except Exception:
        return None


def _keyword_fallback(query: str, top_k: int) -> list[dict]:
    """Simple keyword search over legal_chunks.jsonl."""
    if not _CORPUS_FILE.exists():
        return []
    chunks = []
    for line in _CORPUS_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                chunks.append(json.loads(line))
            except Exception:
                pass
    keywords = [w for w in query.lower().split() if len(w) > 3]
    if not keywords:
        return chunks[:top_k]
    scored = []
    for c in chunks:
        text = (c.get("text", "") + " " + c.get("regulation", "") + " " + c.get("article", "")).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def query(text: str, top_k: int = 5, collections: list[str] | None = None) -> list[dict]:
    """Semantic search across ChromaDB collections.

    Returns list of chunk dicts with an added 'score' key (lower = more similar).
    Falls back to keyword search if ChromaDB unavailable.
    """
    if collections is None:
        collections = ["eu_law", "case_law", "national_law"]

    client, _ = _get_client()
    if client is None:
        return _keyword_fallback(text, top_k)

    results: list[dict] = []
    per_collection = max(1, top_k // len(collections) + 1)

    for col_name in collections:
        col = _get_collection(col_name)
        if col is None:
            continue
        try:
            count = col.count()
            if count == 0:
                continue
            res = col.query(query_texts=[text], n_results=min(per_collection, count))
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            distances = res.get("distances", [[]])[0]
            for doc, meta, dist in zip(docs, metas, distances):
                chunk = dict(meta)
                chunk["text"] = doc
                chunk["score"] = round(dist, 4)
                chunk["_collection"] = col_name
                results.append(chunk)
        except Exception:
            continue

    if not results:
        return _keyword_fallback(text, top_k)

    results.sort(key=lambda x: x.get("score", 1.0))
    return results[:top_k]


def ingest_jsonl(jsonl_path: str = str(_CORPUS_FILE), collection_name: str = "eu_law") -> int:
    """Load all chunks from a JSONL file into a ChromaDB collection.

    Returns number of new chunks added (skips duplicates by id).
    """
    col = _get_collection(collection_name)
    if col is None:
        return 0

    path = Path(jsonl_path)
    if not path.exists():
        return 0

    chunks = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                chunks.append(json.loads(line))
            except Exception:
                pass

    if not chunks:
        return 0

    existing_ids = set(col.get(include=[])["ids"])
    new_chunks = [c for c in chunks if _chunk_id(c) not in existing_ids]

    if not new_chunks:
        return 0

    batch_size = 100
    added = 0
    for i in range(0, len(new_chunks), batch_size):
        batch = new_chunks[i: i + batch_size]
        ids = [_chunk_id(c) for c in batch]
        docs = [c.get("text", "") for c in batch]
        metas = [_safe_meta(c) for c in batch]
        try:
            col.add(ids=ids, documents=docs, metadatas=metas)
            added += len(batch)
        except Exception:
            pass

    return added


def total_chunks() -> int:
    """Return total number of chunks across all collections."""
    client, _ = _get_client()
    if client is None:
        return 0
    total = 0
    for name in ["eu_law", "case_law", "national_law"]:
        col = _get_collection(name)
        if col:
            try:
                total += col.count()
            except Exception:
                pass
    return total


def _chunk_id(chunk: dict) -> str:
    celex = chunk.get("celex_id", "")
    article = chunk.get("article", "")
    reg = chunk.get("regulation", "")
    text_hash = str(abs(hash(chunk.get("text", "")[:50])))
    return f"{celex}-{reg}-{article}-{text_hash}"


def _safe_meta(chunk: dict) -> dict[str, Any]:
    """ChromaDB metadata values must be str, int, float, or bool."""
    safe = {}
    for k, v in chunk.items():
        if k == "text":
            continue
        if isinstance(v, (str, int, float, bool)):
            safe[k] = v
        elif v is None:
            safe[k] = ""
        else:
            safe[k] = str(v)
    return safe
