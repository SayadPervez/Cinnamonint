# Cinnamonint — Design Document

## References

- [Legacy CLINT Analysis](legacy_clint_analysis.md) — deep dive into the original CLINT codebase, architecture, and origin story

---

## 0. AI Instructions

> **Never start coding without approval. Answer queries first and only then, you code once you have approval.**

---

## 1. Core Philosophy

Same as the original CLINT, formalized:

1. **Iterative Sentence Reduction** — User input is a sentence. Known tokens (keywords) are identified. The sentence is split at token boundaries, the token's handler processes its chunk, replaces itself with the result, and the engine loops until no tokens remain.

2. **One Word At A Time** — The system grows by learning one token at a time. Each token is a self-contained unit with its own handler function and test suite.

3. **AI-Assisted Learning** — Unlike the original where the user hand-wrote every handler, an external LLM generates the handler code and tests. The user reviews, approves, and the token is registered. AI only interferes during learning.

4. **Test-Driven Trust** — Every token has test cases derived from common English phrases using that word. New tokens must not break existing tests. This is the guardian against regression.

---

## 2. Architecture

### 2.1 Directory Structure

```
cinnamonint/
├── setup.sh                       # 1st build — install deps, init DB, ready for workshop
├── build.sh                       # 2nd build — produce hardened dist/
├── cinnamonint                    # Entry point runner script
├── requirements.txt               # Pinned + hashed dependencies
├── requirements-dev.txt           # Dev dependencies (pytest)
│
├── src/                           # Source code
│   ├── __init__.py
│   ├── main.py                    # Entry point, REPL loop
│   ├── seed.py                    # Built-in token registration (DO NOT EDIT)
│   ├── engine/                    # Core sentence processing
│   │   ├── __init__.py
│   │   ├── processor.py           # The iterative reduction engine
│   │   ├── tokenizer.py           # Token identification + boundary detection
│   │   ├── resolver.py            # Priority ordering, position-based selection
│   │   ├── spellcheck.py          # Pre-processing spell correction
│   │   └── user_dictionary.py     # User word list (JSON read/write)
│   ├── registry/                  # Token management
│   │   ├── __init__.py
│   │   ├── store.py               # SQLite CRUD for tokens/aliases
│   │   ├── loader.py              # Handler loading + subprocess execution
│   │   └── schema.sql             # DB schema for token registry
│   ├── learn/                     # AI-assisted learning
│   │   ├── __init__.py
│   │   ├── learner.py             # Learn mode orchestration (handover + return flow)
│   │   ├── tester.py              # Test runner for generated handlers
│   │   └── test_setup.py          # Test file scaffolding
│   ├── safety/                    # Guardrails
│   │   ├── __init__.py
│   │   ├── approvals.py           # Command variation approval (hash-based)
│   │   ├── limits.py              # Iteration limits (50/100/200 thresholds)
│   │   └── sandbox.py             # AST-based static analysis
│   ├── cinnamonint_logging/       # Logging system
│   │   ├── __init__.py
│   │   ├── logger.py              # Prompt/result/event logging
│   │   ├── iterations.py          # Per-prompt iteration chain tracking
│   │   └── schema.sql             # DB schema for logs
│   ├── community/                 # Import/export/forget/restore
│   │   ├── __init__.py
│   │   ├── importer.py            # Review + install tokens from local path
│   │   ├── exporter.py            # Package tokens for sharing
│   │   ├── forget.py              # Remove tokens with archive for recovery
│   │   └── restore.py             # Re-import forgotten tokens from archive
│   ├── commands/                   # REPL command handlers
│   │   ├── __init__.py
│   │   ├── dispatch.py            # Command routing + hardened-mode gating
│   │   ├── logs.py                # Log query commands
│   │   └── dictionary.py          # User dictionary management
│   └── config/
│       ├── __init__.py
│       └── settings.py            # Paths, flags, limits, mode detection
│
├── tokens/                        # Handler .py files (one per token)
│   ├── math/                      #   add, plus, subtract, minus, multiply, by, divide, into
│   ├── system/                    #   say, hi, clear, exit
│   └── utility/                   #   wait, now, time, date
│
├── tests/                         # pytest suites mirroring token categories
│   ├── math/
│   ├── system/
│   ├── utility/
│   ├── engine/
│   ├── safety/
│   └── community/
│
├── db/                            # SQLite databases
│   ├── registry.db                # Token registry (Workshop: RW, Hardened: RO)
│   └── logs.db                    # Logs (always writable)
│
├── data/                          # Dictionaries and user data
│   ├── words.txt                  # English dictionary (optional, ~100k words)
│   ├── user_dictionary.json       # User-ignored words
│   └── corrections.json           # Remembered typo→correction mappings
│
├── exports/                       # Exported token packages
├── skills/                        # AI instruction files for learn mode
│   ├── learn.skills.md            # Handler generation prompt template
│   └── learn_flow.skills.md       # Learn flow instructions
│
├── dist/                          # Created by build.sh (2nd build)
│   ├── .cinnamonint_root          # Root marker for path resolution
│   ├── cinnamonint                # Runner script
│   ├── src/                       # Source copy
│   ├── tokens/                    # Handler copy
│   ├── data/                      # Dictionaries copy
│   ├── .venv/                     # Self-contained Python environment
│   └── db/
│       ├── registry.db            # READ-ONLY (chmod 444)
│       └── logs.db                # Fresh, writable (chmod 664)
│
└── legacy/                        # Original CLINT code (reference only)
    └── CLINT/
```

### 2.2 Data Flow

```
User Input
    │
    ▼
┌──────────────────────────────────┐
│  REPL (main.py)                  │
│  - Read input via readline       │
│  - Route through dispatch        │
└─────────┬────────────────────────┘
          │
    ┌─────┴──────────┐
    ▼                ▼
┌──────────┐   ┌───────────────┐
│ Commands │   │ Sentence      │
│ (learn,  │   │ Processing    │
│  forget, │   └──────┬────────┘
│  logs,   │          │
│  etc.)   │          ▼
└──────────┘   ┌───────────────┐
               │ Spell Check   │
               │ (interactive) │
               └──────┬────────┘
                      │
                      ▼
               ┌──────────────────────────────────────┐
               │  Reduction Engine (processor.py)      │
               │  ┌──────────────────────────────────┐ │
               │  │ 1. Build keyword map from DB     │ │
               │  │ 2. Identify tokens in sentence   │ │
               │  │ 3. Resolve priority + position   │ │
               │  │ 4. Check safety approvals        │ │
               │  │ 5. Execute handler (subprocess)  │ │
               │  │ 6. Replace token with result     │ │
               │  │ 7. Log iteration                 │ │
               │  │ 8. Check iteration limits        │ │
               │  │ 9. If tokens remain → goto 2    │ │
               │  │ 10. Output final result          │ │
               │  └──────────────────────────────────┘ │
               └──────────────────────────────────────┘
```

### 2.3 Mode Detection

The system operates in one of two modes, auto-detected at startup:

| Mode | Detection | Capabilities |
|------|-----------|-------------|
| **Workshop** | `registry.db` is writable | Full access — learn, forget, import, restore, export, process, log |
| **Hardened** | `registry.db` is read-only (chmod 444) | Read-only — process, log, export, dictionary. Mutation commands blocked. |

Mode detection uses `os.access(REGISTRY_DB, os.W_OK)`. The `.cinnamonint_root` marker file stops project root resolution at `dist/` boundary to prevent fallback to the workshop project.

---

## 3. Processing Engine (Detail)

### 3.1 The Reduction Loop

```
Input: "add 5, 6 and 7 and subtract 11"

Iteration 1:
  Tokens found: [add (priority 2), subtract (priority 2)]
  Process first: "add"
  Handler input:  "add 5, 6 and 7 and subtract 11"
  Handler output: "18 and subtract 11"

Iteration 2:
  Tokens found: [subtract (priority 2)]
  Process: "subtract"
  Handler input:  "18 and subtract 11"
  Handler output: "7"

Iteration 3:
  Tokens found: []
  No tokens remain → output "7"
```

### 3.2 Handler Function Contract

Every token handler is a Python function with this signature:

```python
def handle(sentence: str) -> str:
    """
    Receives the full current sentence.
    Finds its own keyword, extracts operands, computes result.
    Returns the modified sentence with its operation resolved.
    Must process exactly ONE occurrence of its keyword per call.
    """
```

Why pass the full sentence (not pre-extracted chunks):
- The handler knows its own grammar rules best (e.g., "subtract X from Y" vs "X subtract Y")
- Avoids a complex central parser — each handler IS its own parser
- Matches the original CLINT approach that worked
- LLMs can generate self-contained handlers more reliably this way

### 3.3 Token Priority / Precedence

Tokens have an integer priority value. Higher priority = processed first.

Example:
| Token | Priority | Reason |
|-------|----------|--------|
| `multiply`, `into` | 3 | BODMAS — multiplication before addition |
| `divide`, `by` | 3 | BODMAS |
| `plus`, `add` | 2 | BODMAS |
| `minus`, `subtract` | 2 | BODMAS |
| `say` | 1 | Action — execute after computation |
| `exit` | 0 | Should be last |

When multiple tokens of the same priority exist, process left-to-right (by position in sentence).

### 3.4 Iteration Safety

- **Soft limit: 50 iterations** — Pause, display intermediate sentence state, ask user: "50 iterations reached. Current state: `<sentence>`. Continue? [y/N]"
- If user says yes, another 50 iterations before the next check
- **Hard limit: configurable** (default 200) — Force stop, display state, log as error

### 3.5 Spell Correction (Pre-Processing)

Before the reduction loop begins, the engine runs a spell-check pass. Zero external dependencies — stdlib only + a bundled data file.

**Logic:**

```
For each word in the input:
  1. Is it a known token or alias?          → skip (correct)
  2. Is it a recognized English word?       → skip (correct, just not a token)
  3. Neither → likely a typo
     a. Check difflib.get_close_matches() against all known tokens + aliases
     b. If match found → prompt: "Did you mean 'subtract'? [y/N]"
     c. If user approves → replace in sentence, continue
     d. If no match or user rejects → leave as-is
```

**Implementation:**

| Component | How | Dependencies |
|-----------|-----|-------------|
| Token matching | Direct lookup in registry (tokens + aliases) | `registry.db` |
| English dictionary | Bundled `words.txt` — loaded into a `set()` at startup | ~1MB public domain word list (e.g., `/usr/share/dict/words` or Norvig's corpus) |
| Fuzzy matching | `difflib.get_close_matches(word, token_list, n=3, cutoff=0.7)` | stdlib |

**Rules:**
- Numbers and punctuation are always skipped
- Correction is **always interactive** — never silently autocorrect
- Multiple suggestions shown if close: `Did you mean: subtract, subtract, abstract? [1/2/3/N]`
- Works fully offline in both Workshop and Hardened modes
- The dictionary `set()` is loaded once at startup (~10ms for 100k words)

---

## 4. Token System (Detail)

### 4.1 Token Schema (SQLite: `registry.db`)

```sql
CREATE TABLE tokens (
    id            INTEGER PRIMARY KEY,
    name          TEXT UNIQUE NOT NULL,       -- "plus"
    category      TEXT NOT NULL,              -- "math", "system", "media", ...
    priority      INTEGER DEFAULT 1,          -- processing precedence
    handler_path  TEXT NOT NULL,              -- "tokens/math/plus.py"
    test_path     TEXT,                       -- "tests/math/test_plus.py" (NULL if no tests)
    destructive   BOOLEAN DEFAULT 0,          -- always ask permission?
    downloads     BOOLEAN DEFAULT 0,          -- involves downloading?
    uploads       BOOLEAN DEFAULT 0,          -- involves uploading?
    approved      BOOLEAN DEFAULT 0,          -- has user approved first run?
    author        TEXT DEFAULT 'local',       -- 'local' or community author
    source        TEXT DEFAULT 'seed',        -- 'seed', 'learn', or 'import'
    version       TEXT DEFAULT '1.0.0',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE aliases (
    id        INTEGER PRIMARY KEY,
    token_id  INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    alias     TEXT UNIQUE NOT NULL            -- "add", "+", "sum"
);
```

### 4.2 Handler File Structure

Each handler `.py` file follows a strict template:

```python
"""
Token: plus
Aliases: add, sum, +
Category: math
Priority: 2
Destructive: false
"""

import re

def handle(sentence: str) -> str:
    # Find "plus" keyword
    # Extract numbers on left and right
    # Compute sum
    # Replace this segment with result
    # Return modified sentence
    ...
```

The metadata docstring at the top is parsed during registration but the source of truth is the SQLite registry.

### 4.3 Handler Isolation

Handlers execute in a subprocess (not `exec()` / `eval()` in the main process):

1. Engine writes the current sentence to a temp file or passes as argument
2. Engine runs: `python -c "from tokens.math.plus import handle; print(handle('<sentence>'))"` in a subprocess
3. Captures stdout as the result
4. Timeout: configurable (default 5 seconds per handler call)
5. If handler crashes, the engine catches it, logs the error, and shows the user

This prevents:
- A buggy handler from crashing the entire program
- Memory leaks from accumulating across handlers
- Malicious community-imported handlers from accessing the main process

**Performance trade-off:** Subprocess per handler call adds ~50ms overhead. For most use cases (< 10 iterations), this is imperceptible. For heavy chained operations, we can offer an "unsafe fast mode" in Workshop that uses `importlib` direct import instead (opt-in, not default).

---

## 5. Learn Mode (Detail)

### 5.1 Flow

```
User: "learn subtract"

1. Check if "subtract" already exists → error if yes
2. Call external LLM API with a carefully crafted prompt:
   - "Generate common English phrases using the word 'subtract'"
   - "Generate a Python handler function"
   - "Generate test cases for each phrase"
3. Receive: handler code + test cases
4. Display handler code with syntax highlighting → user reviews
5. Display test cases → user reviews
6. Run all test cases → show results
7. Run ALL existing token test suites → ensure no regressions
8. If all pass AND user approves:
   - Save handler .py file to tokens/
   - Register in SQLite registry
   - Log the learning event
9. If tests fail or user rejects:
   - Show failures
   - Optionally: re-prompt LLM with error context for another attempt
   - Or: user manually edits and re-runs
```

### 5.2 The LLM Prompt

This is critical. The prompt sent to the external LLM needs to produce:

1. **Common phrases** — how is this word used in English?
2. **A handler function** — Python function matching the `handle(sentence: str) -> str` contract
3. **Test cases** — input/output pairs for each phrase

The prompt should include:
- The handler contract (signature, rules)
- Examples of existing handlers (e.g., show the `plus` handler as reference)
- The list of already-registered tokens (so the handler knows what keywords exist and doesn't conflict)
- Rules: "process exactly one occurrence", "return the full modified sentence", "use only Python stdlib"

```
You are generating a token handler for a natural language command processor.

SYSTEM RULES:
- The handler receives a full English sentence as a string
- It must find its keyword ("{token_name}"), extract its operands, compute the result
- It must replace ONLY its own keyword and operands with the result
- It must process exactly ONE occurrence per call
- It must return the full modified sentence
- Use only Python standard library

EXISTING TOKENS (do not conflict): {list_of_existing_tokens}

HANDLER CONTRACT:
```python
def handle(sentence: str) -> str:
    """Process one occurrence of '{token_name}' in the sentence."""
    ...
```

EXAMPLE — the "plus" handler:
{plus_handler_source_code}

TASK:
1. List 10-15 common English phrases using the word "{token_name}"
2. Write the handler function
3. For each phrase, write a test case as: {{"input": "...", "expected": "...", "description": "..."}}

Respond in this exact JSON format:
{{
  "phrases": ["...", ...],
  "handler_code": "def handle(sentence: str) -> str:\n    ...",
  "test_cases": [{{"input": "...", "expected": "...", "description": "..."}}, ...],
  "category": "math|system|media|utility|other",
  "priority": <int>,
  "aliases": ["...", ...],
  "destructive": false,
  "downloads": false,
  "uploads": false
}}
```

### 5.3 Forget Mode

**Seeded tokens** (source = `'seed'`) **cannot be forgotten.** These are the built-in tokens registered by `seed.py`. If the user attempts to forget a seeded token, the command is blocked with a message to re-seed manually.

```
User: "forget subtract"

1. Resolve alias if needed → get canonical token name
2. Check source — if 'seed', block and inform user
3. Confirm with user: "This will remove 'subtract' and all its aliases. Continue? [y/N]"
4. If user confirms:
   - Export full package (manifest + handler + test) to .token_archive/ via export_token()
   - Delete handler .py file from tokens/
   - Delete test .py file from tests/ (if exists)
   - Delete from SQLite registry (cascades to aliases, approvals)
   - Log the forget event
5. Recovery: "restore subtract" re-imports from .token_archive/
```

### 5.4 Restore Mode

```
User: "restore subtract"
  or: "restore" (with no args — lists all archived tokens)

1. If no name given: list all packages in .token_archive/ and return
2. Check .token_archive/<name>/ exists → error if not
3. Re-import the archived package via import_token()
4. Remove the archive directory on success
```

---

## 6. Safety System

### 6.1 Iteration Limit

| Threshold | Action |
|-----------|--------|
| 50 iterations | Pause. Show intermediate state. Ask: "Continue for 50 more?" |
| 100 iterations | Pause again. Warn: "This is unusual." |
| 200 iterations (hard limit) | Force stop. Log as error. Show final state. |

### 6.2 First-Time Command Approval

Approval is tracked at the **command variation level**, not just the token level.

**Example flow:**
1. User runs `abc ./f.txt` → first time this variation is seen → prompt user → approved → stored
2. User runs `abc ./g.txt` → different argument → prompt user → approved → stored
3. User runs `abc ./f.txt` again → already approved → inform user, run without prompting
4. User runs `abc --new-option ./f.txt` → new variation → prompt user → approved → stored

**How it works:**
- When a handler is about to execute, the engine computes a normalized signature of the command (token + key arguments)
- This signature is hashed and checked against the `approvals` table in `registry.db`
- **Hit:** inform user ("Running previously approved: `abc ./f.txt`"), execute
- **Miss:** prompt user ("First time running: `abc ./f.txt`. Approve? [y/N]"), store approval on yes
- From the user's perspective: approve once per unique command variation, never asked again for that exact variation

**Operand-based hashing (flagged tokens):**

Flagged handlers (destructive/downloads/uploads) should implement an `extract_operands(sentence)` function that returns a 3-tuple: `(canonical_token_name, parameters, context)`. The approval system calls this function and hashes the tuple instead of the full sentence, so the same operation in different sentences (e.g., `"upload /images/trip to drive"` vs `"move /trip to /images/ and upload /images/trip to drive"`) produces the same hash and only prompts once.

If the handler doesn't implement `extract_operands`, the system falls back to full-sentence hashing (less precise but still functional). During import, the importer warns if a flagged token lacks this function.

**Schema** (in `registry.db`):

```sql
CREATE TABLE approvals (
    id              INTEGER PRIMARY KEY,
    token_id        INTEGER NOT NULL REFERENCES tokens(id) ON DELETE CASCADE,
    command_hash    TEXT NOT NULL,        -- hash of normalized command signature
    command_display TEXT NOT NULL,        -- human-readable: "abc ./f.txt"
    approved_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(token_id, command_hash)
);
```

### 6.3 Destructive / Download / Upload Commands

- Tokens flagged as `destructive`, `downloads`, or `uploads` in the registry **always** require approval, every single time
- The approval prompt must clearly state what the command will do
- A predefined blocklist of destructive patterns is maintained in config (rm, git clean, git reset, format, shutdown, etc.)
- During learn mode, if the handler code contains any destructive pattern, auto-flag the token

### 6.4 Community Import Safety

- Imported code is ALWAYS shown to user in full with syntax highlighting before registration
- All tests must pass
- The import prompt must state: "This code was written by `<author>`. Review carefully for malicious behavior."
- Static analysis via `ast.parse()` to flag suspicious patterns:
  - `os.system()`, `subprocess.call()` with shell=True
  - File deletions (`os.remove`, `shutil.rmtree`)
  - Network calls (`urllib`, `socket`)
  - `exec()`, `eval()`
  - Environment variable access
- Flagged patterns don't block import — they're highlighted to the user in red

---

## 7. Logging System

### 7.1 Schema (SQLite: `logs.db`)

```sql
-- Every user prompt and its final result
CREATE TABLE prompts (
    id              INTEGER PRIMARY KEY,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_text      TEXT NOT NULL,
    final_output    TEXT,
    iteration_count INTEGER,
    status          TEXT DEFAULT 'ok'    -- 'ok', 'limit_reached', 'error'
);

-- Every iteration of sentence transformation (kept for last 100 prompts)
CREATE TABLE iterations (
    id              INTEGER PRIMARY KEY,
    prompt_id       INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    iteration_num   INTEGER NOT NULL,
    sentence_before TEXT NOT NULL,
    token_processed TEXT,
    handler_path    TEXT,
    sentence_after  TEXT NOT NULL,
    duration_ms     INTEGER,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Learning and forget events
CREATE TABLE learning_events (
    id          INTEGER PRIMARY KEY,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_name  TEXT NOT NULL,
    action      TEXT NOT NULL,          -- 'learn', 'forget', 'import', 'update'
    details     TEXT,                   -- JSON blob with metadata
    source      TEXT DEFAULT 'local'    -- 'local', 'community:<url>'
);

-- Index for fast "last 100 prompts" query
CREATE INDEX idx_prompts_timestamp ON prompts(timestamp DESC);
CREATE INDEX idx_iterations_prompt ON iterations(prompt_id);

-- System execution log — every shell command, file op, network call
CREATE TABLE execution_log (
    id              INTEGER PRIMARY KEY,
    prompt_id       INTEGER REFERENCES prompts(id) ON DELETE SET NULL,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_name      TEXT,
    action_type     TEXT NOT NULL,        -- 'shell', 'file_read', 'file_write',
                                          -- 'file_delete', 'download', 'upload',
                                          -- 'connection'
    command         TEXT,                 -- shell command executed
    path            TEXT,                 -- file path involved (if applicable)
    url             TEXT,                 -- URL involved (if applicable)
    exit_code       INTEGER,              -- shell command exit code
    details         TEXT                  -- additional context (JSON blob)
);

CREATE INDEX idx_exec_log_timestamp ON execution_log(timestamp DESC);
CREATE INDEX idx_exec_log_prompt ON execution_log(prompt_id);
```

### 7.2 Retention Policy

- **Prompts table:** Keep all entries forever (input + final output is small)
- **Iterations table:** Keep detailed iteration chains for the **100 most recent prompts**. Prune older iteration data on each new prompt (keep the prompt row, delete its iterations)
- **Learning events:** Keep forever (these are rare and important)
- **Execution log:** Keep forever (critical audit trail — every shell command, file operation, download/upload, and connection opened)

### 7.3 Log Access Commands

In the REPL:
- `logs recent` — last 20 prompts with their results
- `logs trace <n>` — full iteration trace for prompt #n (if retained)
- `logs learned` — all learning events
- `logs search <query>` — search prompts by text
- `logs exec` — recent execution log (shell commands, file ops, network activity)
- `logs exec <n>` — execution log entries for prompt #n

---

## 8. Build System

### 8.1 `setup.sh` (1st Build → Workshop Mode)

```
What it does:
1. Check Python >= 3.10
2. Create virtualenv in .venv/
3. pip install --require-hashes -r requirements.txt
4. Initialize db/registry.db with schema
5. Initialize db/logs.db with schema
6. Create tokens/ directory structure
7. Print instructions + suggested bash alias:
   echo 'alias cinnamonint="python /path/to/cinnamonint/src/main.py"' >> ~/.bashrc
```

After setup.sh, user can immediately:
- Run the REPL: `cinnamonint` (or `python src/main.py`)
- Learn tokens: `learn plus`
- Use tokens: `5 plus 3`
- Import community tokens: `import <url>`
- View logs: `logs recent`

**No need to navigate into any special directory.** The alias points to main.py which knows its own project root.

### 8.2 `build.sh` (2nd Build → Hardened Mode)

```
What it does:
1. Run ALL token test suites — abort if any fail
2. Create dist/ directory
3. Copy src/ to dist/src/
4. Copy tokens/ to dist/tokens/
5. Copy tests/ to dist/tests/
6. Clone db/registry.db to dist/db/registry.db — set chmod 444 (read-only)
7. Create fresh dist/db/logs.db with schema — chmod 664 (writable)
8. Generate dist/cinnamonint runner script
9. Print instructions + path to dist/
```

**Workshop vs Hardened — feature comparison:**

| Feature | Workshop Mode | Hardened Mode |
|---------|--------------|-----------------|
| Interactive REPL | Yes | Yes |
| Sentence processing | Yes | Yes |
| All safety features | Yes | Yes |
| All logging | Yes | Yes |
| Learn new tokens | Yes | **No** (registry is read-only) |
| Forget tokens | Yes | **No** |
| Import community tokens | Yes | **No** |
| `logs trace` (debug iteration chains) | Yes | Yes |
| Modify handler files | Yes (edit .py directly) | **No** (inform user to go back to workshop) |
| Run test suites manually | Yes | Yes (for verification) |

**The 2nd build is purely optional.** Workshop mode is fully functional. Hardened exists for:
- Distributing to others (friend gets a pre-taught Cinnamonint)
- Security (nobody accidentally teaches it something wrong)
- Slightly faster startup (no learn mode initialization)

---

## 9. Community Token Sharing

### 9.1 Token Package Format

A shareable token is a directory with `.cinnamonint` suffixed files:

```
subtract/
├── manifest.cinnamonint.json   # metadata
├── handler.cinnamonint.py      # the handler function
└── test.cinnamonint.py         # test file (optional)
```

**manifest.cinnamonint.json:**
```json
{
  "name": "subtract",
  "aliases": ["minus", "take away"],
  "category": "math",
  "priority": 2,
  "destructive": false,
  "downloads": false,
  "uploads": false,
  "author": "pervez",
  "version": "1.0.0",
  "description": "Subtraction with natural English syntax"
}
```

### 9.2 Import Flow

```
User: "import /path/to/local/subtract/"
  or: "import /path/to/my-tokens/" (bulk — scans subfolders for packages)

1. Locate manifest.cinnamonint.json in the directory
2. Parse manifest, validate required fields
3. Check for conflicts (name or aliases already registered)
4. Show user: name, author, description, flags
5. Display handler.cinnamonint.py with FULL syntax highlighting
6. Flag suspicious patterns (Section 7.4) in RED
7. Prompt: "This code was written by '<author>'. Approve import? [y/N]"
8. If approved:
   - Copy handler to tokens/<category>/<name>.py
   - Copy test.cinnamonint.py to tests/<category>/test_<name>.py (if present)
   - Register token in DB (with test_path if test file exists)
   - Run the package's tests (parsed from test file)
   - If tests fail: rollback (delete files, remove from DB)
   - If tests pass: log import event
9. If rejected: log rejection
```

### 9.3 Export Flow

```
User: "export subtract"
  or: "export subtract, plus" (multiple)

1. Look up token in registry (resolves aliases)
2. Generate manifest.cinnamonint.json from registry metadata
3. Copy handler .py file as handler.cinnamonint.py
4. Copy test .py file as test.cinnamonint.py (if test_path exists in DB)
5. Package into exports/<name>/ directory
6. Print path to the package
```

Same export logic applies to both seeded and imported tokens. Users share packages via any mechanism — GitHub repos, gists, tarballs, USB drives. No central registry server needed (though one could be built later).

---

## 10. Coding Standards

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Variables | `snake_case` | `token_name`, `handler_path`, `iteration_count` |
| Functions | `snake_case` | `load_handler()`, `run_tests()`, `check_approval()` |
| Classes | `snake_case` with `_` separators | `token_store`, `iteration_logger` — **NO PascalCase** |
| Constants | `UPPER_SNAKE_CASE` | `MAX_ITERATIONS`, `DB_PATH`, `DEFAULT_TIMEOUT` |
| File names | `snake_case` | `processor.py`, `token_store.py` |
| Module/package names | `snake_case` | `src/engine/`, `src/registry/` |

### Absolute Rules

- **No PascalCase or camelCase anywhere** — not in variables, functions, classes, files, or directories
- **All paths relative** — no hardcoded absolute paths; resolve from project root at runtime
- **DRY** — if any logic appears 2+ times, extract it into a function
- **Readable parent functions** — top-level functions should read as a sequence of named function calls, not inline logic. The body tells you *what* happens; the called functions tell you *how*
- **Functions and classes used where appropriate** — use classes when state needs to be grouped and managed; use plain functions for stateless operations
- **No global mutable state** — pass dependencies explicitly
