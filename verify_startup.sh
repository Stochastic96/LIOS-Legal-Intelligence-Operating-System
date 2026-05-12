#!/bin/bash
# LIOS Startup Verification for M1 MacBook
# Run this to verify all prerequisites are met before starting the server

set -euo pipefail

get_lan_ip() {
    ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true
}

LAN_IP="$(get_lan_ip)"

echo "🔍 LIOS Pre-Startup Verification"
echo "=================================="
echo ""

# Check 1: Ollama
echo "✓ Checking Ollama..."
if pgrep -x "ollama" > /dev/null; then
    echo "  ✅ Ollama service is RUNNING"
    if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "  ✅ Ollama API responding"
    else
        echo "  ⚠️ Ollama API not responding yet - wait a moment (http://localhost:11434/api/tags)"
    fi
else
    echo "  ⚠️ Ollama NOT running"
    echo "  Start with: ollama serve"
    exit 1
fi
echo ""

# Check 2: Python & LIOS
echo "✓ Checking Python environment..."
if python3 -c "from lios.orchestration.engine import OrchestrationEngine" 2>/dev/null; then
    echo "  ✅ LIOS modules found"
else
    echo "  ❌ LIOS not installed"
    echo "  Install with: pip install -e '.[dev]'"
    exit 1
fi
echo ""

# Check 3: Port
echo "✓ Checking port 8000..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "  ❌ Port 8000 already in use"
    echo "  Kill with: lsof -i :8000 | grep LISTEN | awk '{print \$2}' | xargs kill -9"
    exit 1
else
    echo "  ✅ Port 8000 available"
fi
echo ""

# Check 4: Models
echo "✓ Checking LLM models..."
MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | wc -l)
if [ "$MODELS" -gt "0" ]; then
    echo "  ✅ Found $MODELS model(s)"
    curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | sed 's/"name":"/    - /' | sed 's/"//'
else
    echo "  ⚠️ No models found - pulling mistral..."
    ollama pull mistral
fi
echo ""

echo "=================================="
echo "✅ All checks passed!"
echo "=================================="
echo ""
echo "Ready to start LIOS. Run:"
echo ""
echo "  uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "Then verify health:"
echo "  curl http://localhost:8000/health"
if [ -n "$LAN_IP" ]; then
    echo "  curl http://$LAN_IP:8000/health"
fi
echo ""
echo "Open in browser: http://localhost:8000/chat"
if [ -n "$LAN_IP" ]; then
    echo "Use on iPhone app (stored in AsyncStorage): http://$LAN_IP:8000"
else
    echo "Use on iPhone app: http://<your-mac-lan-ip>:8000"
fi
echo ""
