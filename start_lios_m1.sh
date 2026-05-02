#!/bin/bash
# LIOS Quick Startup Script for macOS M1
# This script handles the full startup process

set -e

echo "🚀 LIOS M1 Startup Script"
echo "========================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check Ollama
echo -e "${YELLOW}1. Checking Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}✗ Ollama not found${NC}"
    echo "  Install with: brew install ollama"
    exit 1
fi
echo -e "${GREEN}✓ Ollama found: $(ollama --version)${NC}"
echo ""

# Step 2: Check if Ollama is running
echo -e "${YELLOW}2. Checking if Ollama service is running...${NC}"
if pgrep -x "ollama" > /dev/null; then
    echo -e "${GREEN}✓ Ollama service is running${NC}"
else
    echo -e "${YELLOW}⚠ Ollama service not running${NC}"
    echo "  Starting Ollama in a new terminal window..."
    open -a Terminal --new <<EOF
ollama serve
EOF
    echo "  Waiting 10 seconds for Ollama to start..."
    sleep 10
fi
echo ""

# Step 3: Check for models
echo -e "${YELLOW}3. Checking available LLM models...${NC}"
MODELS=$(ollama list 2>/dev/null | tail -n +2 | wc -l)
if [ "$MODELS" -eq 0 ]; then
    echo -e "${YELLOW}⚠ No models found. Installing mistral...${NC}"
    ollama pull mistral
else
    echo -e "${GREEN}✓ Found $MODELS model(s)${NC}"
    ollama list
fi
echo ""

# Step 4: Check Python
echo -e "${YELLOW}4. Checking Python environment...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
echo ""

# Step 5: Install LIOS if needed
echo -e "${YELLOW}5. Checking LIOS installation...${NC}"
if python3 -c "from lios.orchestration.engine import OrchestrationEngine" 2>/dev/null; then
    echo -e "${GREEN}✓ LIOS already installed${NC}"
else
    echo -e "${YELLOW}⚠ Installing LIOS dependencies...${NC}"
    pip install -e ".[dev]" > /dev/null 2>&1
    echo -e "${GREEN}✓ LIOS dependencies installed${NC}"
fi
echo ""

# Step 6: Check port 8000
echo -e "${YELLOW}6. Checking port 8000...${NC}"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}✗ Port 8000 already in use${NC}"
    echo "  Killing process..."
    lsof -Pi :8000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    sleep 2
fi
echo -e "${GREEN}✓ Port 8000 is available${NC}"
echo ""

# Step 7: Start LIOS
echo -e "${YELLOW}7. Starting LIOS API Server...${NC}"
echo -e "${GREEN}✓ Server starting on http://localhost:8000${NC}"
echo ""
echo "=========================================="
echo "🎉 LIOS is ready!"
echo "=========================================="
echo ""
echo "Chat UI:    http://localhost:8000/chat"
echo "API Docs:   http://localhost:8000/docs"
echo "Ollama:     http://localhost:11434"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
uvicorn lios.main:app --host 0.0.0.0 --port 8000 --reload
