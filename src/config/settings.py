"""
Cinnamonint configuration — paths, flags, limits.
All paths are resolved relative to the project root at runtime.
"""

import os


def _find_project_root():
    """walk up from this file until we find AGENTS.md (our root marker)."""
    current = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(current, "AGENTS.md")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            # fallback — two levels up from src/config/
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        current = parent


PROJECT_ROOT = _find_project_root()

# --- database paths ---
DB_DIR = os.path.join(PROJECT_ROOT, "db")
REGISTRY_DB = os.path.join(DB_DIR, "registry.db")
LOGS_DB = os.path.join(DB_DIR, "logs.db")

# --- schema paths ---
REGISTRY_SCHEMA = os.path.join(PROJECT_ROOT, "src", "registry", "schema.sql")
LOGS_SCHEMA = os.path.join(PROJECT_ROOT, "src", "cinnamonint_logging", "schema.sql")

# --- tokens directory ---
TOKENS_DIR = os.path.join(PROJECT_ROOT, "tokens")

# --- tests directory ---
TESTS_DIR = os.path.join(PROJECT_ROOT, "tests")

# --- iteration limits ---
SOFT_ITERATION_LIMIT = 50
WARN_ITERATION_LIMIT = 100
HARD_ITERATION_LIMIT = 200

# --- handler execution ---
HANDLER_TIMEOUT_SECONDS = 5

# --- keyword lookup ---
# sentences with this many words or fewer use per-word DB lookup instead of
# fetching all tokens. keeps memory light as the token registry grows.
WORD_LOOKUP_THRESHOLD = 250

# --- REPL history ---
HISTORY_FILE = os.path.join(PROJECT_ROOT, ".cinnamonint_history")

# --- logging retention ---
ITERATION_RETENTION_COUNT = 100

# --- community ---
EXPORTS_DIR = os.path.join(PROJECT_ROOT, "exports")
TOKEN_ARCHIVE_DIR = os.path.join(PROJECT_ROOT, ".token_archive")

# --- safety: destructive shell patterns ---
# strings checked against string literals inside handler source code
DESTRUCTIVE_PATTERNS = [
    "rm -rf", "rm -r", "rmdir",
    "git clean", "git reset --hard",
    "format c:", "mkfs",
    "dd if=",
    "shutdown", "reboot", "poweroff",
    "> /dev/sda",
    ":(){:|:&};:",
]

# --- mode detection ---
MODE_WORKSHOP = "workshop"
MODE_HARDENED = "hardened"


def detect_mode():
    """determine whether we are running in workshop or hardened mode.

    hardened mode is detected by the registry.db being read-only.
    """
    if not os.path.exists(REGISTRY_DB):
        return MODE_WORKSHOP
    if os.access(REGISTRY_DB, os.W_OK):
        return MODE_WORKSHOP
    return MODE_HARDENED
