# LIOS MacBook Pro M1 Startup Guide

## Quick Start (5 minutes)

### Step 1: Check Your Setup
Run the diagnostics script:
```bash
chmod +x SETUP_DIAGNOSTICS.sh
./SETUP_DIAGNOSTICS.sh
```

This will show:
- ✓ Ollama version and location
- ✓ Available LLM models
- ✓ Ollama service status
- ✓ Python environment
- ✓ Port availability
- ✓ macOS/M1 info

### Step 2: Ensure Ollama is Running
If not running, start it:
```bash
ollama serve
```

This will start Ollama on `http://localhost:11434` (don't close this terminal)

### Step 3: Install LIOS Dependencies (if needed)
In a **new terminal tab**:
```bash
cd /workspaces/LIOS-Legal-Intelligence-Operating-System
pip install -e ".[dev]"
```

### Step 4: Start LIOS API Server
```bash
uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 5: Access the Chat UI
Open your browser:
```
http://localhost:8000/chat
```

---

## Detailed Setup Instructions

### A. Install/Update Ollama (if needed)

**Option 1: Using Homebrew (Recommended for M1)**
```bash
brew install ollama
ollama --version
```

**Option 2: Download from ollama.ai**
Visit https://ollama.ai and download the macOS version

### B. Install an LLM Model

**Recommended models for M1:**

```bash
# Mistral 7B (lightweight, good for M1) - ~5GB
ollama pull mistral

# Or Llama 2 7B
ollama pull llama2

# Or Neural Chat (compact, fast)
ollama pull neural-chat
```

### C. Verify Ollama Service

```bash
# Check if running
ps aux | grep ollama

# Or check HTTP endpoint
curl http://localhost:11434/api/tags

# Expected output shows your models
```

### D. Configure LIOS (optional)

Edit `.env` or set environment variables:
```bash
export LIOS_LLM_ENABLED=true
export LIOS_LLM_PROVIDER=ollama
export LIOS_LLM_HOST=http://localhost:11434
```

### E. Run Tests

```bash
# Quick smoke test
pytest tests/test_orchestration.py -v

# Full test suite
pytest tests/ -v --tb=short
```

---

## Troubleshooting

### "Ollama not found"
- Verify installation: `which ollama`
- Install via Homebrew: `brew install ollama`
- Verify: `ollama --version`

### "Connection refused on port 11434"
- Ollama service not running
- Start it: `ollama serve` (in separate terminal)
- Wait 5 seconds for startup

### "No model available"
- List models: `ollama list`
- Pull a model: `ollama pull mistral`
- Wait for download to complete

### "Port 8000 already in use"
- Kill existing process: `lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9`
- Or use different port: `uvicorn lios.main:app --port 8001`

### "ImportError: No module named 'lios'"
- Install package: `pip install -e ".[dev]"`
- Verify: `python -c "from lios import config; print('✅ LIOS installed')"`

### "sentence-transformers not available" 
- This is normal/optional (shows as WARNING)
- The system will fall back to BM25-only retrieval
- To enable semantic search: `pip install sentence-transformers`

---

## System Requirements (M1 MacBook)

| Component | Requirement | Notes |
|-----------|-------------|-------|
| macOS | 11.0+ | Monterey or later |
| RAM | 8GB minimum | 16GB+ recommended for LLMs |
| Disk | 15GB free | For OS, Python, LLMs |
| Python | 3.10-3.12 | Check: `python3 --version` |
| Ollama | Latest | Apple Silicon native |

---

## Running LIOS Without GPU Issues on M1

By default, Ollama uses GPU acceleration on M1 (optimized). If you experience issues:

```bash
# Run with CPU only (slower but stable)
OLLAMA_CPU=on ollama serve

# Then start LIOS normally
uvicorn lios.main:app --port 8000 --reload
```

---

## Environment Variables

```bash
# LLM Backend
export LIOS_LLM_ENABLED=true                 # Enable/disable LLM
export LIOS_LLM_PROVIDER=ollama              # Provider: ollama | azure
export LIOS_LLM_HOST=http://localhost:11434  # Ollama endpoint

# Chat Mode
export LIOS_CHAT_MODE=simple                 # simple | consensus
export LIOS_CHAT_STORE=jsonl                 # jsonl | postgres

# Development
export LIOS_DEV_MODE=true                    # Verbose logging
export LIOS_AI_AUTO_COMMIT=false             # Auto-commit AI logs to git

# API
export LIOS_API_KEY=your_secret_key          # Optional API key
```

---

## Quick Commands Reference

```bash
# Check Ollama status
curl -s http://localhost:11434/api/tags | python3 -m json.tool

# List models
ollama list

# Pull a model
ollama pull mistral

# Test LIOS import
python3 -c "from lios.orchestration.engine import OrchestrationEngine; print('✅')"

# Run CLI query
lios query "What is CSRD?" --employees 500 --turnover 50000000

# Run API server
uvicorn lios.main:app --reload

# Run tests
pytest tests/ -v
```

---

## Next Steps

1. Run `./SETUP_DIAGNOSTICS.sh` and share output
2. Ensure Ollama is installed and a model is available
3. Start Ollama: `ollama serve`
4. Start LIOS: `uvicorn lios.main:app --port 8000 --reload`
5. Open http://localhost:8000/chat in browser
6. Try the Learn Mode with feedback!

---

## Support

If you encounter issues, please share:
1. Output from `./SETUP_DIAGNOSTICS.sh`
2. Error messages from the terminal
3. `ollama list` output
4. Python version: `python3 --version`

Then I can help debug and configure your setup.
