#!/usr/bin/env bash
# Cinnamonint build.sh — 2nd build (Hardened Mode)
# Runs all tests, then produces a locked-down dist/ folder.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Cinnamonint — Hardened Mode Build      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo

DIST_DIR="$SCRIPT_DIR/dist"

# --- 0. Check for existing dist/ ---
if [ -d "$DIST_DIR" ]; then
    echo -en "${YELLOW}dist/ already exists. Overwrite? [y/N]: ${NC}"
    read -r answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo -e "${RED}Build aborted.${NC}"
        exit 1
    fi
    rm -rf "$DIST_DIR"
    echo -e "  ${GREEN}✓${NC} Removed old dist/"
fi

# --- 1. Activate venv ---
echo -e "${YELLOW}[1/8]${NC} Activating virtual environment..."
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "${RED}ERROR: .venv not found. Run setup.sh first.${NC}"
    exit 1
fi
source "$SCRIPT_DIR/.venv/bin/activate"
echo -e "  ${GREEN}✓${NC} venv activated"

# --- 2. Run all tests ---
echo -e "${YELLOW}[2/8]${NC} Running test suites..."
if ! python -m pytest tests/ --tb=short -q; then
    echo
    echo -e "${RED}BUILD ABORTED — tests failed. Fix them before building.${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} All tests passed"

# --- 3. Create dist/ ---
echo -e "${YELLOW}[3/8]${NC} Creating dist/ directory..."
mkdir -p "$DIST_DIR"
echo -e "  ${GREEN}✓${NC} dist/ created"

# --- 4. Copy source files ---
echo -e "${YELLOW}[4/8]${NC} Copying source files..."
cp -r "$SCRIPT_DIR/src" "$DIST_DIR/src"
cp -r "$SCRIPT_DIR/tokens" "$DIST_DIR/tokens"
cp -r "$SCRIPT_DIR/data" "$DIST_DIR/data"
# copy conftest if it exists (needed for pytest from dist)
[ -f "$SCRIPT_DIR/conftest.py" ] && cp "$SCRIPT_DIR/conftest.py" "$DIST_DIR/conftest.py"
# root marker — tells _find_project_root() to stop here instead of
# walking up into the parent workspace
touch "$DIST_DIR/.cinnamonint_root"
echo -e "  ${GREEN}✓${NC} src/, tokens/, data/ copied"

# --- 5. Set up databases ---
echo -e "${YELLOW}[5/8]${NC} Setting up databases..."
mkdir -p "$DIST_DIR/db"

# clone registry — read-only
cp "$SCRIPT_DIR/db/registry.db" "$DIST_DIR/db/registry.db"
chmod 444 "$DIST_DIR/db/registry.db"

# create fresh logs.db with schema
python -c "
import sys, os
sys.path.insert(0, '$SCRIPT_DIR')
from src.cinnamonint_logging.logger import init_db
# temporarily point to dist logs.db
os.environ['CINNAMONINT_LOGS_DB'] = '$DIST_DIR/db/logs.db'
import sqlite3
schema_path = os.path.join('$SCRIPT_DIR', 'src', 'cinnamonint_logging', 'schema.sql')
conn = sqlite3.connect('$DIST_DIR/db/logs.db')
with open(schema_path) as f:
    conn.executescript(f.read())
conn.close()
print('  databases configured')
"
chmod 664 "$DIST_DIR/db/logs.db"

echo -e "  ${GREEN}✓${NC} registry.db (read-only), logs.db (writable)"

# --- 6. Copy .venv ---
echo -e "${YELLOW}[6/8]${NC} Copying virtual environment..."
cp -r "$SCRIPT_DIR/.venv" "$DIST_DIR/.venv"
echo -e "  ${GREEN}✓${NC} .venv copied (dist is self-contained)"

# --- 7. Generate runner script ---
echo -e "${YELLOW}[7/8]${NC} Generating runner script..."
cat > "$DIST_DIR/cinnamonint" << 'RUNNER'
#!/usr/bin/env bash
# Cinnamonint — hardened mode runner
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/src/main.py" "$@"
RUNNER
chmod +x "$DIST_DIR/cinnamonint"
echo -e "  ${GREEN}✓${NC} dist/cinnamonint is executable"

# --- 8. Clean up __pycache__ ---
echo -e "${YELLOW}[8/8]${NC} Cleaning up..."
find "$DIST_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Cleaned __pycache__"

# --- Summary ---
echo
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  Hardened build complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo
echo -e "Output:  ${CYAN}$DIST_DIR/${NC}"
echo -e "Run:     ${CYAN}$DIST_DIR/cinnamonint${NC}"
echo
echo -e "Registry is ${YELLOW}read-only${NC} — learn, forget, import, restore are disabled."
echo -e "Logging is ${GREEN}writable${NC} — all prompts are still recorded."
echo
