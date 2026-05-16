#!/bin/bash
# LIOS one-command startup.
# Run from the repo root: ./start.sh
# Starts Ollama (if not running), auto-picks a local model, runs a smoke test,
# starts the Python backend, then launches Expo for the mobile app.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "")"
LOCAL_URL="http://localhost:8000"
LAN_URL="http://${LAN_IP:-localhost}:8000"

cleanup() {
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "========================================"
echo "  LIOS — Legal Intelligence OS"
echo "========================================"
echo ""

# ── 1/4  Ollama + model detection ─────────────────────────────────────────────
echo "[1/4] Ollama..."
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "      Not running — starting ollama serve..."
  ollama serve >/dev/null 2>&1 &
  sleep 4
fi

# Pick the best available model from a priority list
DETECTED_MODEL=""
for candidate in mistral:latest llama3.2:3b llama3-fast:latest llama3:latest llama2:latest; do
  base="${candidate%%:*}"
  if ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -q "^${base}"; then
    DETECTED_MODEL="$candidate"
    break
  fi
done

# Last resort: take the first model in the list
if [[ -z "$DETECTED_MODEL" ]]; then
  DETECTED_MODEL="$(ollama list 2>/dev/null | awk 'NR==2{print $1}')"
fi

if [[ -z "$DETECTED_MODEL" ]]; then
  echo ""
  echo "ERROR: No Ollama models found."
  echo "       Pull one first:  ollama pull mistral"
  exit 1
fi

export LIOS_LLM_MODEL="$DETECTED_MODEL"
echo "      OK (model: $LIOS_LLM_MODEL)"

# ── 2/4  Python backend ────────────────────────────────────────────────────────
echo "[2/4] LIOS backend (port 8000)..."

# Kill any leftover process on port 8000
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true

source .venv/bin/activate
mkdir -p logs

uvicorn lios.main:app --host 0.0.0.0 --port 8000 --log-level warning \
  > logs/server.log 2>&1 &
BACKEND_PID=$!

echo -n "      Waiting"
for _ in {1..40}; do
  if curl -sf "$LOCAL_URL/health" >/dev/null 2>&1; then
    echo " ready (PID $BACKEND_PID)"
    break
  fi
  echo -n "."
  sleep 1
done
if ! curl -sf "$LOCAL_URL/health" >/dev/null 2>&1; then
  echo ""
  echo "ERROR: backend did not start. Check logs/server.log:"
  tail -20 logs/server.log
  exit 1
fi

# ── 3/4  LLM smoke test ────────────────────────────────────────────────────────
echo "[3/4] LLM smoke test..."
SMOKE="$(curl -sf --max-time 60 -X POST "$LOCAL_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"What is CSRD in one sentence?","session_id":"startup-test"}' \
  2>/dev/null || echo "")"

if echo "$SMOKE" | grep -qiE "csrd|sustainability|reporting|directive|compliance|corporate"; then
  echo "      OK (LLM responding)"
elif [[ -n "$SMOKE" ]]; then
  echo "      OK (got a response)"
else
  echo "      WARNING: no response from LLM — check logs/server.log if answers seem empty"
fi

# ── Connection info ────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Backend:  $LOCAL_URL"
if [[ -n "$LAN_IP" ]]; then
  echo "  iPhone:   $LAN_URL"
  echo ""
  echo "  iPhone setup (one-time):"
  echo "    1. Open Expo Go — make sure phone is on the same WiFi as this Mac"
  echo "    2. In the LIOS app: Chat tab -> gear icon (top right)"
  echo "    3. Server-Adresse: $LAN_URL"
  echo "    4. API-Key: leave empty"
fi
echo "========================================"
echo ""

# ── 4/4  Expo ─────────────────────────────────────────────────────────────────
echo "[4/4] Expo — scan the QR code below with Expo Go on your iPhone..."
echo ""
cd "$SCRIPT_DIR/lios-mobile"
npx expo start --lan
