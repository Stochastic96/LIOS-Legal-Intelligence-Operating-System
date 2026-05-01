#!/bin/bash
# LIOS — start everything with one command
# Usage: bash start.sh (from project root)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Kill any leftover server on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Activate venv
source .venv/bin/activate

# Get Mac LAN IP and print it
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "unknown")
echo ""
echo "========================================"
echo "  LIOS Starting..."
echo "  Your Mac IP: $IP"
echo "  Set in app:  http://$IP:8000"
echo "========================================"
echo ""

# Start backend in background
uvicorn lios_server:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID) → http://$IP:8000"
sleep 1

# Start Expo in foreground
cd "$SCRIPT_DIR/lios-mobile"
echo "Starting Expo..."
npx expo start

# When expo exits (Ctrl+C), kill backend
echo "Shutting down backend..."
kill $BACKEND_PID 2>/dev/null
