#!/bin/bash
# LIOS — start backend + mobile dev flow for Mac/iPhone/browser use
# Usage: bash start.sh (from project root)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

get_lan_ip() {
  ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true
}

LAN_IP="$(get_lan_ip)"
LOCAL_URL="http://localhost:8000"
LAN_URL="http://${LAN_IP:-localhost}:8000"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Kill any leftover server on port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
  lsof -Pi :8000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
fi

# Activate venv
source .venv/bin/activate

echo ""
echo "========================================"
echo "  LIOS Starting..."
echo "  Browser URL: ${LOCAL_URL}"
if [[ -n "$LAN_IP" ]]; then
  echo "  iPhone URL:  ${LAN_URL}"
else
  echo "  iPhone URL:  (LAN IP not detected; ensure Wi-Fi is connected)"
fi
echo "========================================"
echo ""

if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "✅ Ollama reachable at http://localhost:11434"
else
  echo "⚠️  Ollama not reachable at http://localhost:11434 (start with: ollama serve)"
fi

# Start backend in background (canonical runtime path)
LIOS_UVICORN_TARGET="${LIOS_UVICORN_TARGET:-lios.main:app}"
uvicorn "$LIOS_UVICORN_TARGET" --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Starting backend (PID $BACKEND_PID, target=$LIOS_UVICORN_TARGET)..."
for _ in {1..20}; do
  if curl -fsS "$LOCAL_URL/health" >/dev/null 2>&1; then
    echo "✅ Health OK: $LOCAL_URL/health"
    if [[ -n "$LAN_IP" ]]; then
      echo "✅ iPhone setting: ${LAN_URL}"
      echo "   Verify from Mac with: curl ${LAN_URL}/health"
    fi
    break
  fi
  sleep 1
done
if ! curl -fsS "$LOCAL_URL/health" >/dev/null 2>&1; then
  echo "⚠️  Backend health endpoint not ready yet: $LOCAL_URL/health"
fi

# Start Expo in foreground
cd "$SCRIPT_DIR/lios-mobile"
echo "Starting Expo..."
npx expo start
