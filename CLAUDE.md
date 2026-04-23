# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install (development):**
```bash
pip install -e ".[dev]"
# or with data pipeline tools:
pip install -e ".[dev,data]"
```

**Run the API server:**
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

## Architecture

LIOS is a RAG-based legal intelligence system for EU sustainability compliance (CSRD, ESRS, EU Taxonomy, SFDR, GDPR, BGB, StGB). Queries enter through either the FastAPI API (`lios/api/`) or Click CLI (`lios/cli/`) and are routed through four layers:

**1. Orchestration** (`lios/orchestration/`) — `OrchestrationEngine` is the central coordinator. It uses `QueryParser` to classify intent and routes to either single-agent or consensus mode, then passes results through `ResponseAggregator`.

**2. Analysis** — Two modes:
- *Single-agent* (default): lightweight, fast responses via `lios/intelligence/` (answer synthesis, question classification, fact verification)
- *Consensus mode* (`LIOS_CHAT_MODE=consensus`): three specialist agents (`lios/agents/` — Sustainability, Finance, Supply Chain) run in parallel threads; `ConsensusEngine` requires 2/3 agreement on key entities before returning

**3. Features** (`lios/features/`) — 12 analytical tools (applicability checker, citation engine, compliance roadmap, carbon accounting, materiality, supply chain analysis, etc.) called by agents or directly by the orchestrator.

**4. Knowledge & Retrieval** (`lios/knowledge/`, `lios/retrieval/`) — `RegulatoryDatabase` indexes 7 regulation modules with cached article lookup. `HybridRetriever` is a singleton running 3-stage weighted retrieval: BM25 (0.55) + semantic sentence-transformers (0.30) + provenance rerank (0.15). The corpus lives in `data/corpus/legal_chunks.jsonl` with per-chunk metadata (regulation, article, celex_id, jurisdiction, source_url, version_hash).

**Reasoning** (`lios/reasoning/`) wraps retrieval output in IRAC-structured prompts before synthesis. LLM calls go through `lios/llm/` (Ollama client; falls back to deterministic synthesis if LLM is unavailable).

**Chat sessions** log to `logs/chat_training.jsonl` (JSONL, append-only) and optionally to a PostgreSQL/pgvector backend controlled by `LIOS_CHAT_STORE`.

## Key Configuration

Environment variables (set in shell or `.env`):

| Variable | Effect |
|---|---|
| `LIOS_LLM_ENABLED` | Enable Ollama LLM backend (default: false) |
| `LIOS_LLM_PROVIDER` | `ollama` or `azure` |
| `LIOS_CHAT_MODE` | `simple` (default) or `consensus` |
| `LIOS_DEV_MODE` | Relaxed validation, verbose logging |
| `LIOS_CHAT_STORE` | `jsonl` (default) or `postgres` |

`lios/config.py` → `Settings` class is the single source of truth; all env vars are read there.

## Testing Notes

- pytest-asyncio is configured with `asyncio_mode = auto` (in `pyproject.toml`); no `@pytest.mark.asyncio` decorator needed.
- `tests/conftest.py` provides shared fixtures: `RegulatoryDatabase`, company profiles, pre-built agents.
- Tests are fully offline — no real HTTP calls or LLM calls; `HybridRetriever` and LLM client are mocked/stubbed in fixtures.
- The CI matrix runs Python 3.10, 3.11, and 3.12.
