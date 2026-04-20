---
name: LIOS Legal Intelligence Agent
description: Expert agent for the LIOS (Legal Intelligence Operating System) codebase — an EU sustainability and legal assistant for students, built on FastAPI, Ollama/Mistral, BM25 retrieval, and real EU regulation PDFs.
---

# LIOS Legal Intelligence Operating System — Agent Instructions

## What This Project Is
LIOS is a local-first AI legal assistant for EU sustainability law students.
It runs on a MacBook Pro M1 using Ollama + Mistral 7B instruct, FastAPI, 
BM25 retrieval over real EU regulation PDFs, and a React chat UI.

## Project Structure
- lios/agents/ — specialist AI agents (base_agent, finance, sustainability, supply_chain)
- lios/llm/ — Ollama HTTP client (ollama_client.py)
- lios/retrieval/ — BM25Retriever reading from data/corpus/legal_chunks.jsonl
- lios/ingestion/ — PDF ingestion scripts that build the corpus
- lios/orchestration/ — OrchestrationEngine, FeatureOrchestrator, ResponseComposer
- lios/api/ — FastAPI routes, Pydantic models, dependencies
- lios/prompts/ — system_prompt.txt fed to Mistral
- lios/knowledge/ — structured regulation metadata (NOT the primary knowledge source)
- data/raw_pdfs/ — real EU regulation PDFs (gitignored, not in repo)
- data/corpus/legal_chunks.jsonl — BM25 knowledge base built from PDFs
- data/index/ — FAISS index files (gitignored)
- tests/ — pytest test suite (345 tests passing)

## Tech Stack
- Python 3.10+
- FastAPI + uvicorn
- Ollama running locally at http://localhost:11434
- Model: mistral:7b-instruct-q4_K_M
- BM25 via rank-bm25
- FAISS via faiss-cpu
- sentence-transformers: all-MiniLM-L6-v2
- pypdf for PDF text extraction
- httpx for async HTTP

## Coding Standards — Follow These Always
- Use async def for all FastAPI route handlers
- Use Python type hints on every function signature
- Use Python logging module — never use print() for debug output
- Legal citations format: "Regulation Name, Article X, Paragraph Y"
- Never hardcode regulation thresholds — they belong in lios/knowledge/regulations/config.yaml
- All Pydantic models go in lios/api/models.py
- Ollama base URL is always http://localhost:11434
- Ollama model name is always mistral:7b-instruct-q4_K_M
- Run pytest tests/ -v after every change to confirm nothing is broken

## The RAG Pipeline — How It Must Work
Every user query must flow through exactly this sequence:
1. User query arrives at POST /query
2. BM25Retriever.search(query, top_k=5) retrieves relevant chunks from legal_chunks.jsonl
3. BM25Retriever.format_context(chunks) formats them as readable context
4. Prompt is built: "CONTEXT:\n{context}\n\nQUESTION:\n{query}\n\nANSWER:"
5. call_ollama_sync(prompt) sends to Mistral and returns the answer
6. Response includes: answer (str), sources (list), confidence (str)

## What LIOS Must Never Do
- Never call Ollama without first retrieving BM25 context
- Never cite an article number not present in retrieved context
- Never give definitive legal advice — always frame as educational information
- Never store user data outside logs/chat_training.jsonl
- Never use psycopg2 or pgvector — storage is file-based (FAISS + JSONL)

## EU Regulations in the Knowledge Base
- GDPR (32016R0679) — General Data Protection Regulation
- EU AI Act (32024R1689) — Artificial Intelligence Act
- EU Taxonomy (32020R0852) — Sustainable Finance Taxonomy
- CSRD (32022L2464) — Corporate Sustainability Reporting Directive
- ESRS Set 1 — European Sustainability Reporting Standards

## System Prompt Rules
The file lios/prompts/system_prompt.txt must always instruct Mistral to:
- Only cite articles present in the CONTEXT provided
- Say clearly when context is insufficient
- End every response with the disclaimer line
- Never invent regulation names or article numbers

## Response Format
Every /query response must be JSON with these fields:
{
  "answer": "string — Mistral's response",
  "sources": [{"regulation": "GDPR", "chunk_index": 12, "score": 8.4}],
  "confidence": "verified" | "inferred" | "uncertain",
  "disclaimer": "Educational information only — not legal advice."
}

## M1 MacBook Specific Notes
- Use faiss-cpu (not faiss-gpu) — GPU FAISS not supported on M1 via pip
- sentence-transformers works natively on M1 via MPS — no special config needed
- Ollama runs natively on Apple Silicon — do not set CUDA environment variables
- Virtual environment is at .venv/ — always use .venv/bin/python

## Testing
- Run: pytest tests/ -v
- Integration tests require Ollama running — they auto-skip if Ollama is offline
- Do not break the 345 currently passing tests
- New features must include tests in tests/test_*.py

## Current Priority
The most critical missing piece is: real Ollama calls replacing string assembly.
lios/llm/ollama_client.py must be wired into base_agent.py response generation.
lios/retrieval/bm25_retriever.py must retrieve from the real corpus before every query.
