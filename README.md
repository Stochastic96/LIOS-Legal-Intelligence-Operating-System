# LIOS – Legal Intelligence Operating System

> **AI-powered EU sustainability compliance engine.**
> Zero hallucination via three-agent consensus · Local-first · Cites exact law articles.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What is LIOS?

LIOS is a **local-first Python application** that helps founders, lawyers, and ESG consultants navigate EU sustainability regulations (CSRD, ESRS, EU Taxonomy, SFDR, CSDDD) without hiring a €500/hour legal expert.

It sits between a **legal database and a senior lawyer** — it knows the law precisely, applies it to your specific situation, and shows its work with citations.

### Core differentiators

| Feature | What it does |
|---------|-------------|
| **Three-agent consensus** | Three independent AI agents must agree before an answer is released |
| **Regulatory Decay Scoring** | Every answer comes with a freshness score showing how current the law is |
| **Jurisdiction Conflict Detection** | Automatically spots contradictions between EU law and national law |
| **Applicability Checker** | "Does CSRD apply to us?" — instant, rule-based answer with article citations |
| **Compliance Roadmap** | Personalised, time-ordered action plan with phase-in deadlines |
| **Zero cloud dependency** | SQLite + ChromaDB + Ollama — everything runs on your machine |

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) running locally with `mistral` model (default), **or** an OpenAI API key

### 1. Install

```bash
git clone https://github.com/Stochastic96/LIOS-Legal-Intelligence-Operating-System.git
cd LIOS-Legal-Intelligence-Operating-System
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local Ollama)
```

### 3. Initialise the knowledge base

```bash
# Creates SQLite DB + vector store, ingests CSRD / SFDR / EU Taxonomy sample text
python scripts/setup_kb.py --seed
```

### 4. Start the API

```bash
uvicorn lios.main:app --reload
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Example Usage

### Does CSRD apply to my company?

```bash
curl -X POST http://localhost:8000/compliance/applicability \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyStartup GmbH",
    "employees": 300,
    "turnover_eur": 55000000,
    "balance_sheet_eur": 25000000,
    "jurisdiction": "DE",
    "regulation": "CSRD"
  }'
```

### Ask a legal question

```bash
curl -X POST http://localhost:8000/compliance/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the CSRD double materiality requirements?", "jurisdiction": "DE"}'
```

### Generate a compliance roadmap

```bash
curl -X POST http://localhost:8000/compliance/roadmap \
  -H "Content-Type: application/json" \
  -d '{"name": "AcmeCorp", "employees": 300, "turnover_eur": 60000000, "balance_sheet_eur": 30000000}'
```

---

## Project Structure

```
LIOS-Legal-Intelligence-Operating-System/
├── lios/
│   ├── main.py                    # FastAPI application factory
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── api/
│   │   ├── routes/
│   │   │   ├── compliance.py      # Query, applicability, roadmap, conflicts, breakdown
│   │   │   ├── knowledge_base.py  # Ingest, list, search, delete
│   │   │   └── health.py
│   │   └── middleware/
│   ├── agents/
│   │   ├── orchestrator.py        # Central coordinator
│   │   ├── consensus.py           # Three-agent consensus engine
│   │   ├── specialists/
│   │   │   ├── sustainability_agent.py  # CSRD / ESRS / EU Taxonomy
│   │   │   ├── supply_chain_agent.py    # CSDDD / CBAM
│   │   │   └── finance_agent.py         # SFDR / MiFID II ESG
│   │   └── features/
│   │       ├── decay_scoring.py          # Regulatory freshness score
│   │       ├── jurisdiction_conflict.py  # EU vs. national law conflicts
│   │       ├── citation_engine.py        # EUR-Lex deep-link citations
│   │       ├── applicability_checker.py  # Threshold logic per regulation
│   │       ├── roadmap_generator.py      # Personalised compliance roadmap
│   │       ├── conflict_mapper.py        # Cross-jurisdiction conflict map
│   │       └── legal_breakdown.py        # Section-by-section regulation breakdown
│   ├── knowledge_base/
│   │   ├── manager.py             # Ingestion + retrieval facade
│   │   ├── ingestion/
│   │   │   ├── eurlex_fetcher.py  # EUR-Lex HTTP fetcher
│   │   │   ├── document_parser.py # PDF / HTML / TXT parser
│   │   │   └── preprocessor.py   # Text chunking
│   │   └── indexing/
│   │       ├── embedder.py        # Sentence-transformers embeddings
│   │       └── vector_store.py    # ChromaDB wrapper
│   ├── database/
│   │   ├── connection.py          # SQLAlchemy async engine
│   │   ├── migrations/            # SQL schema
│   │   └── repositories/          # CRUD operations
│   └── utils/
├── data/                          # Runtime data (gitignored)
│   ├── db/                        # SQLite database
│   ├── vector_store/              # ChromaDB embeddings
│   └── regulations/               # Cached EUR-Lex documents
├── scripts/
│   ├── setup_kb.py               # One-command KB initialisation
│   ├── ingest_regulations.py     # Fetch from EUR-Lex
│   └── export_kb.py              # JSON backup
├── training/
│   ├── datasets/                  # Q&A pairs + benchmark
│   ├── fine_tuning/               # LoRA fine-tuning pipeline
│   └── evaluation/                # ROUGE + citation metrics
├── tests/
│   ├── test_agents/               # Consensus + feature module tests
│   ├── test_knowledge_base/       # Preprocessing + metrics tests
│   └── test_api/                  # End-to-end API tests
└── docs/
    ├── architecture.md
    ├── api_reference.md
    ├── knowledge_base_guide.md
    └── future_scope.md
```

---

## Running Tests

```bash
pytest
```

---

## Fetching Real Regulations from EUR-Lex

```bash
# Requires internet access
python scripts/ingest_regulations.py                     # all known regs
python scripts/ingest_regulations.py --regulation SFDR   # single regulation
```

---

## Configuration Reference

See `.env.example` for all settings. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LIOS_LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `LIOS_OLLAMA_MODEL` | `mistral` | Ollama model name |
| `LIOS_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `LIOS_CONSENSUS_THRESHOLD` | `0.67` | Min. agent agreement fraction |
| `LIOS_DECAY_THRESHOLD_DAYS` | `365` | Days before freshness score → 0 |

---

## Documentation

| Doc | Contents |
|-----|---------|
| [Architecture](docs/architecture.md) | System design, data flow diagrams |
| [API Reference](docs/api_reference.md) | All endpoints with examples |
| [Knowledge Base Guide](docs/knowledge_base_guide.md) | Ingestion, search, updating |
| [Future Scope](docs/future_scope.md) | Roadmap and research directions |
| [Training Guide](training/README.md) | Fine-tuning and evaluation |

---

## License

MIT

