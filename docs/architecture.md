# LIOS System Architecture

## Overview

LIOS is a three-layer, local-first Python application:

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: API (FastAPI)                                          │
│  /compliance/query  /compliance/applicability  /compliance/roadmap │
│  /compliance/conflicts  /compliance/breakdown  /kb/*             │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  Layer 2: Orchestration Engine                                   │
│  Orchestrator → ConsensusEngine + 7 Feature Modules             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │Sustainability│  │SupplyChain   │  │Finance               │   │
│  │Agent        │  │Agent         │  │Agent                 │   │
│  └─────────────┘  └──────────────┘  └──────────────────────┘   │
│  Features: DecayScorer · ConflictDetector · CitationEngine      │
│            ApplicabilityChecker · RoadmapGenerator              │
│            ConflictMapper · LegalBreakdownEngine                │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  Layer 3: Data                                                   │
│  SQLite (regulations + queries)  ChromaDB (vector embeddings)   │
│  EUR-Lex documents cached to disk                               │
└─────────────────────────────────────────────────────────────────┘
```

## Component Map

| Component | File | Purpose |
|-----------|------|---------|
| `Orchestrator` | `lios/agents/orchestrator.py` | Central coordinator – retrieval → agents → consensus → enrichment |
| `ConsensusEngine` | `lios/agents/consensus.py` | Pairwise similarity voting across three agents |
| `SustainabilityAgent` | `lios/agents/specialists/sustainability_agent.py` | CSRD / ESRS / EU Taxonomy expert |
| `SupplyChainAgent` | `lios/agents/specialists/supply_chain_agent.py` | CSDDD / CBAM / supply chain expert |
| `FinanceAgent` | `lios/agents/specialists/finance_agent.py` | SFDR / MiFID II ESG expert |
| `DecayScorer` | `lios/agents/features/decay_scoring.py` | Regulation freshness scoring |
| `JurisdictionConflictDetector` | `lios/agents/features/jurisdiction_conflict.py` | EU vs. national law conflicts |
| `CitationEngine` | `lios/agents/features/citation_engine.py` | EUR-Lex deep-link citations |
| `ApplicabilityChecker` | `lios/agents/features/applicability_checker.py` | Regulation threshold logic |
| `RoadmapGenerator` | `lios/agents/features/roadmap_generator.py` | Personalised compliance roadmap |
| `ConflictMapper` | `lios/agents/features/conflict_mapper.py` | Cross-jurisdiction conflict map |
| `LegalBreakdownEngine` | `lios/agents/features/legal_breakdown.py` | Section-by-section regulation breakdown |
| `KnowledgeBaseManager` | `lios/knowledge_base/manager.py` | Ingestion + semantic search facade |
| `EurLexFetcher` | `lios/knowledge_base/ingestion/eurlex_fetcher.py` | EUR-Lex HTTP fetcher |
| `VectorStore` | `lios/knowledge_base/indexing/vector_store.py` | ChromaDB wrapper |
| `Embedder` | `lios/knowledge_base/indexing/embedder.py` | Sentence-transformers embeddings |

## Data Flow: Query Resolution

```
User query
   │
   ▼
Orchestrator.handle(query)
   │
   ├─► KnowledgeBaseManager.search()   [ChromaDB cosine search]
   │       └─► top_k regulation chunks retrieved
   │
   ├─► Agent fan-out (parallel)
   │       ├─ SustainabilityAgent.respond()
   │       ├─ SupplyChainAgent.respond()
   │       └─ FinanceAgent.respond()
   │
   ├─► ConsensusEngine.evaluate()
   │       ├─ AGREE → merged_answer (highest confidence)
   │       └─ DISAGREE → conflict_summary (no answer released)
   │
   ├─► DecayScorer.aggregate()        [freshness score]
   ├─► CitationEngine.enrich()        [EUR-Lex URLs]
   ├─► ConflictMapper.map()           [jurisdiction gaps]
   │
   └─► QueryRepository.create()       [persist to SQLite]
           └─► OrchestratorResponse returned to API
```

## LLM Provider Configuration

LIOS supports two LLM backends, configured via `LIOS_LLM_PROVIDER`:

| Provider | Setting | Notes |
|----------|---------|-------|
| Ollama (default) | `LIOS_LLM_PROVIDER=ollama` | Fully local, no cost |
| OpenAI | `LIOS_LLM_PROVIDER=openai` | Requires `LIOS_OPENAI_API_KEY` |

## Storage

| Store | Technology | Location |
|-------|-----------|---------|
| Regulations & queries | SQLite (async via aiosqlite) | `data/db/lios.db` |
| Vector embeddings | ChromaDB (persistent) | `data/vector_store/` |
| Raw regulation documents | Plain text files | `data/regulations/` |
