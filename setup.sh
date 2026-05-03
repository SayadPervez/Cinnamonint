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
echo -e "${YELLOW}[1/8]${NC} Checking Python version..."
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
echo -e "${YELLOW}[2/8]${NC} Creating virtual environment..."
if [ -d ".venv" ]; then
    echo -e "  ${GREEN}✓${NC} .venv already exists"
else
    "$PYTHON" -m venv .venv
    echo -e "  ${GREEN}✓${NC} Created .venv/"
fi

# activate
source .venv/bin/activate

# --- 3. Install dependencies ---
echo -e "${YELLOW}[3/8]${NC} Installing dependencies..."
pip install --require-hashes -r requirements.txt --quiet
pip install --require-hashes -r requirements-dev.txt --quiet
echo -e "  ${GREEN}✓${NC} Dependencies installed (runtime + dev)"

# --- 4. Create directory structure ---
echo -e "${YELLOW}[4/8]${NC} Creating directories..."
mkdir -p db tokens/math tokens/system tokens/utility tests
echo -e "  ${GREEN}✓${NC} Directory structure ready"

# --- 5. Initialize databases ---
echo -e "${YELLOW}[5/8]${NC} Initializing databases..."
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
echo -e "${YELLOW}[6/8]${NC} Seeding built-in tokens..."
python src/seed.py
echo -e "  ${GREEN}✓${NC} Built-in tokens registered"

# --- 7. Optional English dictionary for enhanced spell correction ---
echo -e "${YELLOW}[7/8]${NC} Enhanced spell correction..."
DICT_FILE="$SCRIPT_DIR/data/words.txt"
if [ -f "$DICT_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} Dictionary already present ($(wc -l < "$DICT_FILE") words)"
else
    echo -en "  Download English dictionary for enhanced spell correction? (~1 MB) [y/N]: "
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        mkdir -p "$SCRIPT_DIR/data"
        # try system dictionary first, then download
        if [ -f /usr/share/dict/words ]; then
            cp /usr/share/dict/words "$DICT_FILE"
            echo -e "  ${GREEN}✓${NC} Copied system dictionary ($(wc -l < "$DICT_FILE") words)"
        else
            DICT_URL="https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
            if curl -fsSL "$DICT_URL" -o "$DICT_FILE" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Downloaded dictionary ($(wc -l < "$DICT_FILE") words)"
            elif wget -q "$DICT_URL" -O "$DICT_FILE" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Downloaded dictionary ($(wc -l < "$DICT_FILE") words)"
            else
                echo -e "  ${YELLOW}⚠${NC} Download failed — spell correction will use token-only mode"
                rm -f "$DICT_FILE"
            fi
        fi
    else
        echo -e "  ${CYAN}↦${NC} Skipped — spell correction will use token-only mode"
    fi
fi

# --- 8. Make entry point executable ---
echo -e "${YELLOW}[8/8]${NC} Setting up entry point..."
chmod +x "$SCRIPT_DIR/cinnamonint"
echo -e "  ${GREEN}✓${NC} ./cinnamonint is executable"

echo
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete! Workshop mode ready.${NC}"
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo
echo -e "To start Cinnamonint:"
echo -e "  ${CYAN}./cinnamonint${NC}"
echo
echo -e "Or add it to your PATH:"
echo -e "  ${CYAN}ln -s $SCRIPT_DIR/cinnamonint ~/.local/bin/cinnamonint${NC}"
echo
echo -e "To run tests:"
echo -e "  ${CYAN}python -m pytest tests/ -v${NC}"
