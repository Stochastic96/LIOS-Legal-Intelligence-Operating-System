#!/bin/bash
# LIOS Setup Diagnostics for macOS M1
# Run this script to collect system information for troubleshooting

echo "=========================================="
echo "LIOS Setup Diagnostics - macOS M1"
echo "=========================================="
echo ""

echo "1. Checking Ollama Installation..."
echo "---"
if command -v ollama &> /dev/null; then
    echo "✓ Ollama found at: $(which ollama)"
    ollama --version
else
    echo "✗ Ollama not found in PATH"
fi
echo ""

echo "2. Checking Available LLM Models..."
echo "---"
if command -v ollama &> /dev/null; then
    ollama list
else
    echo "⚠ Ollama not installed - cannot list models"
fi
echo ""

echo "3. Checking Ollama Service Status..."
echo "---"
if pgrep -x "ollama" > /dev/null; then
    echo "✓ Ollama service is RUNNING (PID: $(pgrep -x ollama))"
else
    echo "⚠ Ollama service is NOT running"
fi
echo ""

echo "4. Checking Python Environment..."
echo "---"
python3 --version
echo "Python path: $(which python3)"
echo ""

echo "5. Checking LIOS Installation..."
echo "---"
if [ -f "pyproject.toml" ]; then
    echo "✓ LIOS project found (pyproject.toml present)"
    echo "Project name: $(grep '^name = ' pyproject.toml | head -1)"
else
    echo "⚠ LIOS pyproject.toml not found"
fi
echo ""

echo "6. Checking Port Availability..."
echo "---"
echo "Port 8000 (LIOS API):"
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "  ✗ BUSY (PID: $(lsof -Pi :8000 -sTCP:LISTEN -t))"
else
    echo "  ✓ Available"
fi
echo ""

echo "7. System Information..."
echo "---"
echo "OS: $(sw_vers -productName) $(sw_vers -productVersion)"
echo "Chip: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'M1/M2/M3 (auto-detected)')"
echo "Memory: $(sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}')"
echo ""

echo "=========================================="
echo "Diagnostics complete!"
echo "=========================================="
