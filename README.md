# LIOS-Legal-Intelligence-Operating-System
Legal Intelligence Operating System for EU sustainability compliance. Instant answers on CSRD, ESRS, EU Taxonomy. Every answer cites exact law articles.

## Local Chat Studio (UI + training capture)

Use LIOS fully local from your PC browser. No cloud account is required.

### 1) Install and run

```bash
pip install -r requirements.txt
uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

- `http://localhost:8000/chat` (same machine)
- `http://localhost:8000/chat-react` (React UI, no build step)
- `http://<your-machine-ip>:8000/chat` (another device on your network)
- Alias URL: `http://localhost:8000/chat-ui`

By default, the chat starts in single-agent mode so the first conversation stays focused and does not fan out to the other specialist agents. To enable the full three-agent consensus path, set `LIOS_CHAT_MODE=consensus` before launching.

### 2) Start chat-based training workflow

In the chat workspace:

- send legal questions,
- optionally provide company profile JSON,
- keep a stable Session ID while iterating,
- export JSONL when done.

All turns are saved locally at `logs/chat_training.jsonl` and can be used as a prompt-tuning / eval dataset.

V2 behavior notes:

- Normal user questions run in lightweight mode by default (concise + citation-backed answer).
- Heavy outputs (freshness/conflict scans) are skipped unless explicit context requires deeper analysis.
- Chat sessions use direction hints after repeated turns to keep follow-up answers focused.
- Seed training examples are available in `data/training/v2_seed_chat.jsonl`.

### V2.1 Data + Retrieval Foundation

This repo now includes a provenance-aware legal corpus and a 3-stage hybrid retriever:

- Stage A: BM25 lexical retrieval (`rank-bm25`) for legal precision
- Stage B: Optional semantic retrieval (`sentence-transformers`) for semantic coverage
- Stage C: Grounded reranking that favors chunks with strong source provenance

Provenance chunk fields include:

- `source_url`
- `celex_or_doc_id`
- `jurisdiction`
- `regulation`
- `article`
- `published_date`
- `effective_date`
- `version_hash`
- `ingestion_timestamp`

Bootstrap corpus file:

- `data/corpus/legal_chunks.jsonl`

Rebuild corpus from built-in regulation modules:

```bash
python -m lios.ingestion.build_seed_corpus
```

Install data pipeline dependencies (optional group):

```bash
pip install -e .[data]
```

### Troubleshooting quick checks

If `/chat` returns `404 Not Found`, verify loaded routes:

```bash
curl http://localhost:8000/debug/routes
```

You should see `/chat` in the JSON response. You can also use:

- `http://localhost:8000/health` (server health)
- `http://localhost:8000/docs` (OpenAPI docs)

If browser shows `Failed to connect`, check host/port quickly:

```bash
curl -i http://127.0.0.1:8000/health
```

If that fails, restart on a free port:

```bash
uvicorn lios.main:app --host 127.0.0.1 --port 8010 --reload
```

Then open `http://127.0.0.1:8010/chat-react`.
