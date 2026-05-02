# LIOS M1 MacBook - Quick Reference Card

## 🚀 Fastest Way to Start (Copy & Paste)

### Terminal 1: Start Ollama
```bash
ollama serve
```

### Terminal 2: Start LIOS
```bash
cd /workspaces/LIOS-Legal-Intelligence-Operating-System
chmod +x start_lios_m1.sh
./start_lios_m1.sh
```

Then open: **http://localhost:8000/chat**

---

## 🔍 Diagnose Your Setup

```bash
chmod +x SETUP_DIAGNOSTICS.sh
./SETUP_DIAGNOSTICS.sh
```

This shows:
- Ollama version & models
- Service status
- Python environment
- Port availability

---

## ⚙️ Manual Startup (if script doesn't work)

### Terminal 1: Ollama
```bash
# Check if installed
ollama --version

# Start service
ollama serve

# Expected: "Listening on 127.0.0.1:11434"
```

### Terminal 2: LIOS Dependencies
```bash
pip install -e ".[dev]"
```

### Terminal 3: LIOS API
```bash
cd /workspaces/LIOS-Legal-Intelligence-Operating-System
uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload
```

### Browser
Open: http://localhost:8000/chat

---

## 🛠️ Common Issues

| Problem | Solution |
|---------|----------|
| `ollama: command not found` | `brew install ollama` |
| `Connection refused:11434` | Start Ollama: `ollama serve` |
| `No models available` | `ollama pull mistral` |
| `Port 8000 in use` | Kill process: `lsof -i :8000 \| grep LISTEN \| awk '{print $2}' \| xargs kill -9` |
| `Import error: lios` | Install: `pip install -e ".[dev]"` |

---

## 📋 What to Share If Issues

Run this and share the output:
```bash
./SETUP_DIAGNOSTICS.sh
```

Also share:
- Error messages from terminal
- Output of: `ollama list`
- Output of: `python3 --version`

---

## 🎯 Key Endpoints

| URL | Purpose |
|-----|---------|
| http://localhost:8000/chat | Chat UI (Serve + Learn Mode) |
| http://localhost:8000/docs | API Documentation |
| http://localhost:11434 | Ollama health check |

---

## 📚 Learn Mode Features

Once running at http://localhost:8000/chat:

1. **Toggle Learn Mode** - Click "Learn" button in sidebar
2. **Ask Questions** - Type your legal compliance questions
3. **Give Feedback** - ✓ Correct, ✗ Incorrect, ~ Partial, ? Unclear
4. **View Status** - See accuracy, topics, knowledge gaps
5. **Get Questions** - Click "Next Question" for adaptive learning
6. **Session Summary** - Click "Session Summary" for detailed report

---

## 🔑 Environment Variables (Optional)

```bash
export LIOS_LLM_ENABLED=true
export LIOS_CHAT_MODE=simple  # or: consensus
export LIOS_DEV_MODE=true     # for verbose logging
```

Then start LIOS normally.

---

## 📱 First Query to Try

Once the app loads, ask in the chat:
```
What is CSRD and who needs to comply with it?
```

Or set company profile:
```
Employees: 1000
Turnover: €500,000,000
Listed: Yes
Jurisdiction: Germany
```

Then ask:
```
Does CSRD apply to our company?
```

---

## ✅ Checklist

- [ ] Ollama installed (`brew install ollama`)
- [ ] Model downloaded (`ollama list` shows model)
- [ ] Ollama running (`ollama serve` in terminal)
- [ ] LIOS dependencies installed (`pip install -e ".[dev]"`)
- [ ] API server running (`uvicorn lios.main:app ...`)
- [ ] Browser opens http://localhost:8000/chat
- [ ] Chat loads and shows "Workspace ready"
- [ ] Toggle to Learn Mode
- [ ] Try a question and provide feedback

---

## 💡 Tips

- **Ollama Command** must stay running in its terminal (don't close it)
- **First Query** may take 5-10 seconds while LLM loads
- **Learn Mode** doesn't require feedback API key (local setup)
- **Logs** appear in terminal window where uvicorn runs
- **GPU** on M1 is automatically used (fast!)
- **CPU Only** if needed: `OLLAMA_CPU=on ollama serve`

---

**Questions?** Run the diagnostics and share output - I can help troubleshoot!
