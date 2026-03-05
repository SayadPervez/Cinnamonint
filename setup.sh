#!/usr/bin/env bash
# Cinnamonint setup.sh — 1st build (Workshop Mode)
# Checks Python, creates venv, installs deps, initializes DBs, seeds tokens.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         Cinnamonint — Workshop Setup         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo

# --- 1. Check Python >= 3.10 ---
echo -e "${YELLOW}[1/6]${NC} Checking Python version..."
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        major=$("$candidate" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
        minor=$("$candidate" -c "import sys; print(sys.version_info.minor)" 2>/dev/null)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}ERROR: Python 3.10+ is required. Found none.${NC}"
    echo "Install Python 3.10 or newer and try again."
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Found $PYTHON ($version)"

# --- 2. Create virtual environment ---
echo -e "${YELLOW}[2/6]${NC} Creating virtual environment..."
if [ -d ".venv" ]; then
    echo -e "  ${GREEN}✓${NC} .venv already exists"
else
    "$PYTHON" -m venv .venv
    echo -e "  ${GREEN}✓${NC} Created .venv/"
fi

# activate
source .venv/bin/activate

# --- 3. Install dependencies ---
echo -e "${YELLOW}[3/6]${NC} Installing dependencies..."
pip install --require-hashes -r requirements.txt --quiet
pip install --require-hashes -r requirements-dev.txt --quiet
echo -e "  ${GREEN}✓${NC} Dependencies installed (runtime + dev)"

# --- 4. Create directory structure ---
echo -e "${YELLOW}[4/6]${NC} Creating directories..."
mkdir -p db tokens/math tokens/system tokens/utility tests
echo -e "  ${GREEN}✓${NC} Directory structure ready"

# --- 5. Initialize databases ---
echo -e "${YELLOW}[5/6]${NC} Initializing databases..."
python -c "
import sys, os
sys.path.insert(0, '.')
from src.registry.store import init_db as init_registry
from src.cinnamonint_logging.logger import init_db as init_logs
init_registry()
init_logs()
print('  databases initialized')
"
echo -e "  ${GREEN}✓${NC} registry.db and logs.db ready"

# --- 6. Seed built-in tokens ---
echo -e "${YELLOW}[6/6]${NC} Seeding built-in tokens..."
python src/seed.py
echo -e "  ${GREEN}✓${NC} Built-in tokens registered"

echo
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete! Workshop mode ready.${NC}"
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo
echo -e "To start Cinnamonint:"
echo -e "  ${CYAN}source .venv/bin/activate${NC}"
echo -e "  ${CYAN}python src/main.py${NC}"
echo
echo -e "Or add an alias to your shell config:"
echo -e "  ${CYAN}alias cinnamonint='cd $SCRIPT_DIR && source .venv/bin/activate && python src/main.py'${NC}"
echo
echo -e "To run tests:"
echo -e "  ${CYAN}python -m pytest tests/ -v${NC}"
