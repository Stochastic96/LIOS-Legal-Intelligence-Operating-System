# Knowledge Base Guide

## Overview

The LIOS knowledge base has two storage layers:

| Layer | Technology | Contents |
|-------|-----------|---------|
| Relational | SQLite (`data/db/lios.db`) | Full regulation text, metadata, query history |
| Vector | ChromaDB (`data/vector_store/`) | Text chunk embeddings for semantic search |

Both layers are populated together via the `KnowledgeBaseManager`.

---

## Quick Start

### 1. Initialise the KB (first run)

```bash
python scripts/setup_kb.py           # creates DB + empty vector store
python scripts/setup_kb.py --seed    # also ingests CSRD, SFDR, EU Taxonomy sample text
```

### 2. Fetch from EUR-Lex (network required)

```bash
python scripts/ingest_regulations.py                  # all known regulations
python scripts/ingest_regulations.py --regulation CSRD
```

### 3. Ingest a local file

```bash
python scripts/ingest_regulations.py \
    --file data/regulations/my_regulation.pdf \
    --short-name CSRD
```

### 4. Via the API

```bash
curl -X POST http://localhost:8000/kb/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "CSRD – Directive 2022/2464",
    "short_name": "CSRD",
    "framework": "CSRD",
    "content": "Article 1 – Subject matter..."
  }'
```

### 5. Export / backup

```bash
python scripts/export_kb.py --output my_backup.json
```

---

## Supported Frameworks

| Short Name | Regulation | CELEX |
|-----------|-----------|-------|
| `CSRD` | Corporate Sustainability Reporting Directive | 32022L2464 |
| `SFDR` | Sustainable Finance Disclosure Regulation | 32019R2088 |
| `EU_TAXONOMY` | EU Taxonomy Regulation | 32020R0852 |
| `CSDDD` | Corporate Sustainability Due Diligence Directive | 32024L1760 |
| `CBAM` | Carbon Border Adjustment Mechanism | 32023R0956 |
| `ESRS` | European Sustainability Reporting Standards | 32023R2772 |
| `OTHER` | Custom / national regulation | – |

---

## Chunking Strategy

Regulation texts are split into overlapping chunks (default: 1,500 chars, 200-char overlap).
Article headings within each chunk are auto-detected and stored as `article_ref` metadata.

The overlap ensures that article boundaries don't cut off relevant context.

---

## Updating Regulations

When a regulation is amended:

1. Re-fetch from EUR-Lex: `python scripts/ingest_regulations.py --regulation CSRD`
2. The regulation is upserted (same ID, updated content + `last_verified_at`)
3. Vector store chunks are replaced via ChromaDB's `upsert` operation

The Decay Scorer will automatically reflect the updated `last_verified_at` date.

---

## Semantic Search

The KB uses `all-MiniLM-L6-v2` (sentence-transformers) by default.
This model runs entirely locally (~90 MB) and produces 384-dimensional embeddings.

To use a different model, set `LIOS_EMBEDDING_MODEL` in `.env`.

**Note:** Changing the embedding model requires re-indexing all regulations
(reset the vector store and re-run ingestion).
