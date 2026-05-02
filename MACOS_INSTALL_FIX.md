# macOS M1 LIOS Installation Fix

## Problem
You're getting `ModuleNotFoundError: No module named 'rank_bm25'` when trying to start LIOS.

## Root Cause
`rank-bm25` and other retrieval/data pipeline dependencies are marked as **optional** in `pyproject.toml`. You need to install them explicitly.

## Solution

### Step 1: Install All Dependencies
Navigate to your LIOS directory and install with the optional `data` extras:

```bash
# First, navigate to your LIOS folder (adjust path to match your setup)
cd ~/Desktop/LIOS-Legal-Intelligence-Operating-System-1

# Install ALL dependencies including optional data tools
pip install -e ".[dev,data]"
```

This will install:
- ✅ `rank-bm25>=0.2.2` (BM25 retriever)
- ✅ `sentence-transformers>=2.7.0` (semantic search)
- ✅ `faiss-cpu>=1.8.0` (vector indexing)
- ✅ `sqlalchemy>=2.0.30` (database ORM)
- ✅ All other dev and data tools

### Step 2: Verify Installation
```bash
# Check rank-bm25 is installed
python3 -c "from rank_bm25 import BM25Okapi; print('✓ rank-bm25 installed')"
```

### Step 3: Start LIOS

**In Terminal 1** (Ollama server - keep running):
```bash
ollama serve
```

**In Terminal 2** (LIOS API):
```bash
cd ~/Desktop/LIOS-Legal-Intelligence-Operating-System-1
uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Access LIOS
Open your browser and go to: **http://localhost:8000/chat**

## What the Extras Do

| Extra | Purpose | Key Packages |
|-------|---------|--------------|
| `dev` | Testing & development | pytest, pytest-asyncio |
| `data` | **Retrieval & embeddings** | **rank-bm25, sentence-transformers, faiss-cpu** |
| `llm` | (Optional) OpenAI integration | openai |

## Troubleshooting

### If pip install fails with "Permission denied"
Use your Python environment's pip (not system):
```bash
# Find your Python
which python3

# Use that directly
/path/to/python3 -m pip install -e ".[dev,data]"
```

### If uvicorn still can't start
1. Check all imports work:
   ```bash
   python3 -c "from lios.main import app; print('✓ All imports OK')"
   ```

2. Check Ollama is running:
   ```bash
   curl http://127.0.0.1:11434/api/tags
   ```

3. Check port 8000 is free:
   ```bash
   lsof -i :8000
   ```

### If you see "Ollama address already in use"
The Ollama server is already running (good!). Just open Terminal 2 and start the LIOS API.

## Expected Output After Successful Start

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete
```

Then open http://localhost:8000/chat in your browser.

---

**Need more help?** Run this to show your environment:
```bash
python3 -c "import sys; print(sys.executable); print(sys.version)"
pip list | grep -E "rank-bm25|sentence|faiss"
```
