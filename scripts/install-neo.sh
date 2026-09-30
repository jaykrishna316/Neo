#!/bin/bash

# Neo Installation Script
# One-command setup for Neo testing on desktop

set -e

echo "=========================================================="
echo "Neo - Semantic Multi-Developer Coordination Engine"
echo "Installation Script"
echo "=========================================================="
echo ""

# Step 1: Check prerequisites
echo "[1] Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "   Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION found"

if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed"
    echo "   Please install Git"
    exit 1
fi

echo "✓ Git is installed"
echo ""

# Step 2: Create virtual environment
echo "[2] Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""

# Step 3: Activate and install dependencies
echo "[3] Installing dependencies..."
source .venv/bin/activate
python3 -m pip install --quiet --upgrade pip setuptools
python3 -m pip install --quiet -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Step 4: Verify installation
echo "[4] Verifying installation..."

python3 -c "import mcp; print('  ✓ MCP SDK found')" 2>/dev/null || echo "  ⚠️  MCP SDK"
python3 -c "import watchdog; print('  ✓ Watchdog found')" 2>/dev/null || echo "  ⚠️  Watchdog"
python3 -c "import requests; print('  ✓ Requests found')" 2>/dev/null || echo "  ⚠️  Requests"
python3 -c "from core.activity_log import log_activity; print('  ✓ Activity log module found')" 2>/dev/null || echo "  ⚠️  Activity log"
python3 -c "from core.pre_gen_check import check_for_conflicts; print('  ✓ Conflict detection found')" 2>/dev/null || echo "  ⚠️  Conflict detection"

echo ""

# Step 5: Final status
echo "=========================================================="
echo "✅ Neo Installation Complete!"
echo "=========================================================="
echo ""
echo "📂 Neo is ready at:"
echo "   $(pwd)"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. ACTIVATE virtual environment (run this in each new terminal):"
echo "   source .venv/bin/activate"
echo ""
echo "2. RUN quick test:"
echo "   python tests/test_two_developer_coordination.py"
echo ""
echo "3. OR run full 2-developer terminal test:"
echo "   See: docs/LOCAL_TWO_DEVELOPER_TEST.md"
echo ""
echo "=========================================================="
