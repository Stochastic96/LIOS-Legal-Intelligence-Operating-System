# LIOS — Claude Code Rules

## AI Tracking (MANDATORY — Read This First)

**Before making any change to this codebase, every AI session must:**

1. **Check** `logs/ai_tracking.jsonl` — read the last entry to understand what was done previously and what is unfinished
2. **Append a `session_start` entry** to `logs/ai_tracking.jsonl` with:
   - `session_id` (format: `lios-<descriptor>-<YYYYMMDD>`)
   - `ai_model` (which model you are)
   - `timestamp` (ISO 8601 UTC)
   - `task` (what you are about to do)
   - `goal` (what completing this achieves for the user)
   - `completed_steps` (carry forward from previous session if resuming)
   - `remaining_steps` (full list of what is left)
   - `current_step` (the first thing you will do)
3. **Append a `step_complete` entry** each time a step finishes
4. **Append a `session_end` entry** when finishing normally, with `stop_reason: "completed"` or `stop_reason: "user_request"`
5. **If context limit is approaching** (you notice you are running out of context), immediately append a `session_interrupted` entry with:
   - `stop_reason: "context_limit"`
   - `current_step`: exactly what you were doing mid-task
   - `completed_steps`: everything finished so far
   - `remaining_steps`: everything still left
   - `resume_instructions`: precise instructions for the next AI session to pick up exactly where you left off — file paths, function names, what was partially written

**The tracking log must never be deleted. It is the institutional memory of all AI work on this codebase.**

### Entry format (append-only JSONL)
```json
{"event":"session_start"|"step_complete"|"session_end"|"session_interrupted", "session_id":"...", "ai_model":"...", "timestamp":"...", "task":"...", "goal":"...", "current_step":"...", "completed_steps":[...], "remaining_steps":[...], "stop_reason":null|"completed"|"user_request"|"context_limit"|"error", "resume_instructions":"..."}
```

---

## Project Overview

**LIOS (Legal Intelligence Operating System)** — a self-learning EU sustainability law assistant.

- Backend: FastAPI + Python, runs on `uvicorn lios.main:app --port 8000`
- LLM: Ollama (local, Mistral) wired via `lios/llm/refiner.py`
- Knowledge: 33 EU law chunks in `data/corpus/legal_chunks.jsonl` (CSRD, ESRS, EU Taxonomy, SFDR)
- Mobile: React Native + Expo Go app in `lios-mobile/` (connects over WiFi to backend)
- Storage: JSON/JSONL files only — no external database

## Key Directories

```
lios/api/routes.py          — all FastAPI endpoints
lios/orchestration/engine.py — query routing + LLM refinement
lios/llm/refiner.py         — Ollama/Azure LLM integration
lios/features/chat_training.py — chat session storage
data/corpus/legal_chunks.jsonl — EU law knowledge base
data/memory/                — corrections.json, rules.json, knowledge_map.json (created at runtime)
logs/ai_tracking.jsonl      — AI session tracking (this file)
lios-mobile/                — Expo React Native app
```

## Architecture Decisions

- No database — everything is JSON/JSONL files
- Brain toggle is runtime (no restart needed), stored in `data/memory/brain_state.json`
- Memory rules are injected into the LLM system prompt on every query when brain is ON
- Expo app connects to `http://<MAC_IP>:8000` over LAN — user sets IP in app settings
- Knowledge map pre-seeded with EU law topics; topics graduate: `unknown → learning → connected → functional → mastered`

## Coding Style

- Python: dataclasses, type hints, no external DB dependencies
- Keep new endpoints in `lios/api/routes.py` following existing patterns
- New feature modules go in `lios/features/`
- New memory/state modules go in `lios/memory/` (create if needed)
- React Native: functional components, hooks only, no class components
- No comments unless the WHY is non-obvious

## Running the Stack

```bash
# Backend
cd LIOS-Legal-Intelligence-Operating-System
source .venv/bin/activate
uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload

# Ollama (separate terminal)
ollama run mistral

# Expo app
cd lios-mobile
npx expo start
```
