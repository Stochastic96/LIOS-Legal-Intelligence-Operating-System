# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install (development):**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# with data pipeline tools (FAISS, sentence-transformers, BM25, etc.):
pip install -e ".[dev,data]"
# with LLM client (openai package):
pip install -e ".[dev,llm]"
```

**One-command startup (Ollama + backend + Expo mobile):**
```bash
./start.sh
```
`start.sh` requires a `.venv` virtualenv at the repo root (it sources `.venv/bin/activate`) and checks that `llama3.2:3b` is available via Ollama (`ollama pull llama3.2:3b`). The active model used for LLM calls is controlled by `LIOS_LLM_MODEL` (default: `mistral:latest`). Starts backend on port 8000; logs to `logs/server.log`.

**Verify prerequisites before starting:**
```bash
bash verify_startup.sh
```

**Run the API server only:**
```bash
uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload
```

**Run all tests:**
```bash
pytest tests/ -v --tb=short
```

**Run a single test:**
```bash
pytest tests/test_agents.py::TestSustainabilityAgent::test_name -v
```

**Lint:**
```bash
ruff check lios/ tests/
```

**CLI:**
```bash
lios query "What is CSRD?" --employees 500 --turnover 50000000
```

**Corpus / data pipeline scripts** (in `scripts/`):
```bash
python scripts/build_corpus.py          # rebuild legal_chunks.jsonl
python scripts/ingest_pdfs.py           # ingest PDF files into corpus
python scripts/autolearn.py             # run auto-trainer pipeline
python scripts/export_finetune.py       # export chat logs for fine-tuning
```

## Corpus Artifacts (Git LFS)

The corpus files (`data/corpus/legal_chunks.jsonl`, `.embeddings.npy`, `.faiss`) are tracked with Git LFS. If they appear as pointer files after cloning, run `git lfs pull`. Confirm the retriever loads non-zero chunks via `GET /health`.

## Architecture

LIOS is a RAG-based legal intelligence system for EU sustainability compliance (CSRD, ESRS, EU Taxonomy, SFDR, GDPR, BGB, StGB). Queries enter through either the FastAPI API (`lios/api/`) or Click CLI (`lios/cli/`) and are routed through four layers:

**1. Orchestration** (`lios/orchestration/`) — `OrchestrationEngine` is the central coordinator. It uses `QueryParser` to classify intent and routes to either single-agent or consensus mode, then passes results through `ResponseAggregator`.

**2. Analysis** — Two modes:
- *Single-agent* (default): `UnifiedComplianceAgent` (`lios/agents/unified_agent.py`) handles all domains; lightweight, fast responses refined by `lios/intelligence/` (answer synthesis, question classification, fact verification) and polished by `lios/llm/refiner.py` which applies the full LIOS system prompt.
- *Consensus mode* (`LIOS_CHAT_MODE=consensus`): three specialist agents (`lios/agents/` — Sustainability, Finance, Supply Chain) run in parallel threads; `ConsensusEngine` requires 2/3 agreement on key entities before returning.

**3. Features** (`lios/features/`) — 12 analytical tools (applicability checker, citation engine, compliance roadmap, carbon accounting, materiality, supply chain analysis, decay scoring, jurisdiction conflict, etc.) called by agents or directly by the orchestrator.

**4. Knowledge & Retrieval** (`lios/knowledge/`, `lios/retrieval/`) — `RegulatoryDatabase` indexes 7 regulation modules with cached article lookup. `HybridRetriever` is a module-level singleton (loaded once per process) running 3-stage weighted retrieval: BM25 (0.55) + semantic `all-MiniLM-L6-v2` sentence-transformers (0.30) + provenance rerank (0.15). Document embeddings are computed once at construction and persisted to disk (`.embeddings.npy`, `.faiss`). The corpus lives in `data/corpus/legal_chunks.jsonl` with per-chunk metadata (regulation, article, celex_id, jurisdiction, source_url, version_hash).

**Reasoning** (`lios/reasoning/`) wraps retrieval output in IRAC-structured prompts (Issue–Rule–Analysis–Conclusion) before synthesis. Every `build_prompt()` call accepts a `lens` parameter selecting one of five analytical perspectives: `compliance` (obligations, thresholds, deadlines), `risk` (penalties, liability), `drafter` (exact definitions, scope, exceptions), `impact` (who is affected, what must change), `interpretive` (CJEU precedent, legal principles, conflicts). LLM calls go through `lios/llm/` via an OpenAI-compatible client pointing at Ollama by default; falls back to deterministic `AnswerSynthesizer` if LLM is unavailable.

**Answer routing** (`lios/main.py::generate_answer`) — easy questions (definitions, general law) go LLM-direct, then verify grounding with `FactVerifier`; complex questions (applicability, roadmap, breakdown) go RAG-first. `run_pipeline()` in the same file is an alternative FAISS-dense-retrieval path that requires `lios[data]`.

**Memory & Learning** (`lios/memory/`, `lios/learning/`) — `brain_state.py` persists LLM on/off state to `data/memory/brain_state.json` for runtime toggle without server restart. `KnowledgeMap` tracks what LIOS has learned. `GapDetector` identifies knowledge gaps (UNKNOWN → MASTERED scale) and generates smart questions. `FeedbackHandler` and `LearningEventStore` record training data from user interactions. `scripts/autolearn.py` runs a producer/consumer pipeline to continuously grow the corpus.

**Chat sessions** log to `logs/chat_training.jsonl` (JSONL, append-only) and optionally to SQLite (`LIOS_CHAT_STORE_BACKEND=sqlite`).

## API Structure

The FastAPI app (`lios/api/routes.py`) mounts sub-routers from `lios/api/routers/`:

| Router | Prefix / purpose |
|---|---|
| `core` | `/health`, `/query`, core compliance queries |
| `chat` | `/chat` — main conversational endpoint |
| `learn` | `/learn` — Learn Mode / gap-driven Q&A |
| `intelligence` | `/intelligence` — mobile intelligence API |
| `carbon` | `/carbon` — GHG / carbon accounting |
| `supply_chain` | `/supply-chain` — supply chain analysis |
| `impact` | `/impact` — impact assessment |
| `dashboard` | `/dashboard` — aggregated metrics |

Authentication: set `LIOS_API_KEY` to require `X-API-Key` header. CORS origins controlled by `LIOS_CORS_ALLOWED_ORIGINS` (default: `*`).

## Mobile App

`lios-mobile/` is a React Native / Expo app (Expo Go, owner: `stochastic96`). `archive/mobile-expo/` is the legacy client — not supported for daily use. `./start.sh` starts Expo alongside the backend. The server URL and API key are stored via `AsyncStorage` in `lios-mobile/src/api/client.ts`; to connect on an iPhone: Chat tab → gear icon → Server-Adresse → enter `http://<LAN_IP>:8000`. If LAN mode fails, switch Expo to tunnel mode by pressing `s` in the Expo terminal.

## Key Configuration

Environment variables (all prefixed `LIOS_`, read by `lios/config.py::Settings`):

| Variable | Default | Effect |
|---|---|---|
| `LIOS_LLM_ENABLED` | `true` | Enable LLM backend |
| `LIOS_LLM_PROVIDER` | `openai_compatible` | `openai_compatible` (Ollama) or `azure` |
| `LIOS_LLM_BASE_URL` | `http://localhost:11434/v1` | Ollama/compatible endpoint |
| `LIOS_LLM_MODEL` | `mistral:latest` | Model name |
| `LIOS_CHAT_MODE` | `simple` | `simple` or `consensus` |
| `LIOS_API_KEY` | *(empty)* | When set, enables `X-API-Key` auth |
| `LIOS_DEV_MODE` | `false` | Exposes `/debug/routes`, verbose logging |
| `LIOS_CHAT_STORE_BACKEND` | `jsonl` | `jsonl` or `sqlite` |
| `AZURE_OPENAI_ENDPOINT` etc. | *(empty)* | Used when `LIOS_LLM_PROVIDER=azure` |
| `LIOS_TOKEN_BUDGET_DEFAULT` | `800` | Max output tokens for unclassified queries |
| `LIOS_TOKEN_BUDGET_ROADMAP` | `1500` | Max tokens for roadmap/timeline answers |
| `LIOS_TOKEN_BUDGET_DEFINITION` | `512` | Max tokens for definition answers |

`lios/config.py` → `Settings` dataclass is the single source of truth; `"ollama"` is normalised to `"openai_compatible"` on load. Per-intent token budgets are also configurable via `LIOS_TOKEN_BUDGET_APPLICABILITY`, `LIOS_TOKEN_BUDGET_BREAKDOWN`, and `LIOS_TOKEN_BUDGET_GENERAL_LAW`.

## Testing Notes

- pytest-asyncio is configured with `asyncio_mode = auto` (in `pyproject.toml`); no `@pytest.mark.asyncio` decorator needed.
- `tests/conftest.py` provides shared fixtures: `RegulatoryDatabase`, company profiles, pre-built agents.
- Tests are fully offline — no real HTTP calls or LLM calls; `HybridRetriever` and LLM client are mocked/stubbed in fixtures.
- The CI matrix runs Python 3.10, 3.11, and 3.12.
