#!/bin/bash
# LIOS One-Step Startup for M1 MacBook
# Just run this and it handles everything

cd /workspaces/LIOS-Legal-Intelligence-Operating-System

echo "🚀 Starting LIOS..."
echo ""
echo "This script will:"
echo "  1. Verify Ollama is running"
echo "  2. Install dependencies if needed"
echo "  3. Check SSL libraries"
echo "  4. Start the API server on port 8000"
echo ""

# Check Ollama
if ! pgrep -x "ollama" > /dev/null; then
    echo "❌ Ollama not running. Please start it first:"
    echo "   ollama serve"
    exit 1
fi

echo "✅ Ollama is running"

# Install dependencies silently
if ! python3 -c "from lios.orchestration.engine import OrchestrationEngine" 2>/dev/null; then
    echo "📦 Installing LIOS dependencies..."
    pip install -e ".[dev]" > /dev/null 2>&1
    echo "✅ Dependencies installed"
else
    echo "✅ LIOS dependencies already installed"
fi

# Check port
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 in use. Freeing it..."
    lsof -Pi :8000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null
    sleep 1
fi

echo ""
echo "=========================================="
echo "🎉 Starting LIOS API Server"
echo "=========================================="
echo ""
echo "Chat UI:  http://localhost:8000/chat"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start server
uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload
