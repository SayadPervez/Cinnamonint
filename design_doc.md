# Cinnamonint — Design Document

> **Status:** Design Phase (no code yet)
> **Date:** 1 March 2026

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

## 2. Design Decisions

### 2.1 TUI vs CLI

| Factor | CLI + Rich | Full TUI (Textual/Curses) |
|--------|-----------|--------------------------|
| Primary interaction (REPL) | Native fit — just stdin/stdout | Over-engineered for a prompt loop |
| Learn mode (code review) | `rich` syntax highlighting, scrollable | Split-panel layout — nice but heavyweight |
| Piping / scripting | `echo "5 plus 3" \| cinnamonint` just works | Breaks piping entirely |
| Terminal compatibility | Works in any terminal | Requires modern terminal with mouse support |
| SSH / remote use | Works perfectly | Rendering issues common |
| Startup time | Instant | Framework initialization overhead |
| Implementation effort | Low — use `rich` for pretty output | Medium-High — layout management, event loops |
| Scrollback & history | Terminal handles it natively | Must reimplement manually |

**Recommendation: CLI with `rich`.**
The core interaction is a REPL — type a sentence, get a response. A full TUI adds complexity without meaningful benefit. `rich` gives us syntax highlighting (critical for learn mode code review), tables, markdown rendering, and colored output with a single dependency.

---

### 2.2 Database for Logs

| Factor | SQLite | JSON Lines (.jsonl) | CSV |
|--------|--------|---------------------|-----|
| Append performance | O(1) insert | O(1) append | O(1) append |
| Query "last 100 iterations for prompt #42" | Single SQL query | Parse entire file | Parse entire file |
| Built into Python | Yes (`sqlite3` in stdlib) | Yes (`json` in stdlib) | Yes (`csv` in stdlib) |
| Concurrent write safety | WAL mode handles it | Manual file locking needed | Manual file locking needed |
| Structured nested data (iteration chains) | Foreign keys + indexes | Nested objects (messy to query) | Not possible — flat only |
| Prune old data (keep N recent) | `DELETE WHERE` | Rewrite entire file | Rewrite entire file |
| Human-readable | No (binary file) | Yes | Yes |
| Size efficiency | Good (B-tree, compressed) | Verbose (repeated keys) | Compact |

**Recommendation: SQLite.**
Logs need structured querying (iterations per prompt, recent N prompts, learning events). SQLite handles this natively with zero setup. WAL mode gives safe concurrent writes. It's in Python's stdlib. The "not human-readable" downside doesn't matter — we'll build query commands into the CLI for inspecting logs.

---

### 2.3 Database for Token Registry

| Factor | SQLite | JSON file | TOML file |
|--------|--------|-----------|-----------|
| Token lookup by name | O(1) with index | O(n) load + search | O(n) load + search |
| Relationships (token → aliases, tests, metadata) | Foreign keys, normalized | Nested objects, denormalized | Nested tables, limited nesting |
| Read-only lockdown (2nd build) | `chmod 444` on file | `chmod 444` on file | `chmod 444` on file |
| Scales to 1000+ tokens | Easily | Single file bloats, slow parse | Multiple files get messy |
| Community export/import | Query → JSON package | Copy + merge (conflict-prone) | Copy + merge |
| Human-editable for debugging | No | Yes | Yes |
| Atomic operations (add token + tests in one transaction) | Native transactions | Manual file write (corruption risk on crash) | Same risk |

**Recommendation: SQLite for registry metadata + individual `.py` files for handler code.**

Why the hybrid:
- SQLite stores: token name, aliases, priority, category, metadata, handler file path, test file path, destructive flag, approval state
- Individual `.py` files store: the actual handler function code AND test suites
- This gives us: fast indexed lookup AND git-friendly diffs on handler code AND human-readable source files AND easy community sharing (a token = .py file + metadata JSON)

---

### 2.4 Programming Language

| Factor | Python | Node.js (JavaScript) | Hybrid (Python + JS) |
|--------|--------|---------------------|----------------------|
| String / text manipulation | First-class — slicing, f-strings, `re` | Adequate but more verbose | N/A |
| Dynamic function loading | `importlib.import_module()` — native | `require()`, `eval()` — works | Two runtimes to manage |
| Stdlib coverage for this project | `sqlite3`, `json`, `re`, `os`, `subprocess`, `unittest`, `urllib`, `ast` — **covers ~95%** | Far less built-in; need npm packages for basics | Worst of both |
| External deps needed | `rich` (1 package) | Several npm packages minimum | Multiple in both ecosystems |
| Supply chain attack surface | 1 well-audited dep (`rich` — 14k+ GitHub stars, Textualize team) | npm ecosystem has higher incident rate; more deps = more surface | Both attack surfaces combined |
| Startup time | ~80ms | ~50ms | ~200ms+ (two runtimes) |
| LLM code generation quality | Python is the #1 language for LLM codegen — handlers will be more correct | Good but second to Python for this domain | Confusing for LLM (which lang?) |
| Token author community | Natural fit — AI/NLP/scripting audience | Different audience | Splits community |
| Sandboxing executed code | `subprocess` isolation + `ast.parse()` static analysis | `vm2` deprecated; `isolated-vm` exists | Mixed |
| User's existing knowledge | Strong (wrote CLINT in Python) | Unknown | Overhead |
| Dep pinning / hash verification | `pip install --require-hashes -r requirements.txt` | `npm ci` with `package-lock.json` | Both systems |

**Recommendation: Python.**
The core mechanism is dynamically loading and executing token handler functions generated by an LLM. Python is the most natural language for this — `importlib` for loading, `ast` for static analysis before execution, `subprocess` for sandboxed runs, and LLMs produce the highest-quality Python code. One external dependency (`rich`) keeps the supply chain surface minimal.

**Supply chain mitigation plan:**
- Pin exact versions with hashes in `requirements.txt`
- `rich` is the only external runtime dependency — well-maintained by the Textualize team
- For the AI API calls: use stdlib `urllib.request` (no `requests` package needed)
- Token handler files use stdlib only by default; if a handler needs an external package, it's flagged during import review

---

### 2.5 Build Scripts & Mode Names

| Option | Setup Script | Build Script | Mode After Setup | Mode After Build |
|--------|-------------|-------------|-----------------|-----------------|
| A | `setup.sh` | `build.sh` | Workshop | Hardened |
| B | `forge.sh` | `seal.sh` | Forge | Sealed |
| C | `init.sh` | `bundle.sh` | Dev | Production |
| D | `setup.sh` | `pack.sh` | Workshop | Packed |

**Recommendation: Option A — `setup.sh` / `build.sh`, Workshop Mode / Hardened Mode.**

Reasoning:
- `setup.sh` / `build.sh` are universally understood; no learning curve
- "Workshop" conveys the right mental model — you're in a workspace where you build, teach, test, and tinker
- "Hardened" conveys the output — locked down, tamper-proof, no modifications allowed
- Avoids "dev/prod" which implies web deployment connotations

---

## 3. Architecture

### 3.1 Directory Structure

```
cinnamonint/
├── AGENTS.md                      # This file — design document
├── legacy_clint_analysis.md       # Analysis of original CLINT
├── setup.sh                       # 1st build — install deps, init DB, ready for workshop
├── build.sh                       # 2nd build — produce hardened dist/
├── requirements.txt               # Pinned + hashed dependencies
│
├── src/                           # Source code
│   ├── __init__.py
│   ├── main.py                    # Entry point, REPL loop
│   ├── engine/                    # Core sentence processing
│   │   ├── __init__.py
│   │   ├── processor.py           # The iterative reduction engine
│   │   ├── tokenizer.py           # Token identification in sentences
│   │   └── resolver.py            # Alias resolution, priority ordering
│   ├── registry/                  # Token management
│   │   ├── __init__.py
│   │   ├── store.py               # SQLite registry operations
│   │   ├── loader.py              # Dynamic handler loading (importlib)
│   │   └── schema.sql             # DB schema for token registry
│   ├── learn/                     # AI-assisted learning
│   │   ├── __init__.py
│   │   ├── learner.py             # Learn mode orchestration
│   │   ├── prompts.py             # LLM prompt templates
│   │   ├── generator.py           # Code generation via external LLM
│   │   └── tester.py              # Test runner for generated handlers
│   ├── safety/                    # Guardrails
│   │   ├── __init__.py
│   │   ├── approvals.py           # First-run and destructive command gating
│   │   ├── limits.py              # Iteration limit (50) with user prompt
│   │   └── sandbox.py             # Static analysis + subprocess isolation
│   ├── cinnamonint_logging/               # Logging system (renamed from logging/ — see §15)
│   │   ├── __init__.py
│   │   ├── logger.py              # Core logging (prompts, results, events)
│   │   ├── iterations.py          # Per-prompt iteration chain tracking
│   │   └── schema.sql             # DB schema for logs
│   ├── community/                 # Import/export/forget/restore
│   │   ├── __init__.py
│   │   ├── importer.py            # Download + review + install tokens
│   │   ├── exporter.py            # Package tokens for sharing
│   │   ├── forget.py              # Remove tokens with archive for recovery
│   │   └── restore.py             # Re-import forgotten tokens from archive
│   └── config/
│       ├── __init__.py
│       └── settings.py            # Configuration (API keys, paths, flags)
│
├── tokens/                        # Handler .py files (one per token)
│   ├── math/
│   │   ├── plus.py
│   │   ├── minus.py
│   │   └── ...
│   ├── system/
│   │   ├── exit.py
│   │   └── ...
│   └── ...
│
├── db/                            # SQLite databases
│   ├── registry.db                # Token registry (Workshop: read-write)
│   └── logs.db                    # Logs (always read-write)
│
├── tests/                         # Token test suites
│   ├── test_plus.py
│   ├── test_minus.py
│   └── ...
│
├── dist/                          # Created by build.sh (2nd build)
│   ├── cinnamonint                        # Runner script
│   ├── src/                       # Source copy
│   ├── tokens/                    # Handler copy
│   ├── db/
│   │   ├── registry.db            # READ-ONLY copy
│   │   └── logs.db                # Fresh, writable
│   └── tests/                     # Test copy (for verification)
│
└── legacy/                        # Original CLINT code
    └── CLINT/
```

### 3.2 Data Flow

```
User Input
    │
    ▼
┌──────────────────────────────────┐
│  REPL (main.py)                  │
│  - Read input                    │
│  - Detect mode keywords          │
│    ("learn X", normal sentence)  │
└─────────┬────────────────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐ ┌──────────────┐
│ Learn  │ │ Interactive   │
│ Mode   │ │ Mode          │
└───┬────┘ └──────┬───────┘
    │             │
    ▼             ▼
┌────────────┐ ┌──────────────────────────────────────┐
│ LLM API    │ │  Processing Engine                    │
│ Generate   │ │  ┌──────────────────────────────────┐ │
│ handler +  │ │  │ 1. Resolve aliases               │ │
│ tests      │ │  │ 2. Identify tokens in sentence   │ │
│     │      │ │  │ 3. Pick highest-priority token   │ │
│     ▼      │ │  │ 4. Load handler, execute on      │ │
│ Show code  │ │  │    sentence                      │ │
│ Run tests  │ │  │ 5. Replace with result            │ │
│ User       │ │  │ 6. Log iteration                 │ │
│ approves?  │ │  │ 7. If tokens remain AND          │ │
│     │      │ │  │    iterations < 50 → goto 2     │ │
│     ▼      │ │  │ 8. Output final result           │ │
│ Register   │ │  └──────────────────────────────────┘ │
│ token      │ │                                        │
└────────────┘ └──────────────────────────────────────┘
```

---

## 4. Processing Engine (Detail)

### 4.1 The Reduction Loop

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

### 4.2 Handler Function Contract

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

### 4.3 Token Priority / Precedence

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

### 4.4 Iteration Safety

- **Soft limit: 50 iterations** — Pause, display intermediate sentence state, ask user: "50 iterations reached. Current state: `<sentence>`. Continue? [y/N]"
- If user says yes, another 50 iterations before the next check
- **Hard limit: configurable** (default 200) — Force stop, display state, log as error

### 4.5 Spell Correction (Pre-Processing)

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

## 5. Token System (Detail)

### 5.1 Token Schema (SQLite: `registry.db`)

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

### 5.2 Handler File Structure

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

### 5.3 Handler Isolation

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

## 6. Learn Mode (Detail)

### 6.1 Flow

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

### 6.2 The LLM Prompt

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

### 6.3 Forget Mode

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

### 6.4 Restore Mode

```
User: "restore subtract"
  or: "restore" (with no args — lists all archived tokens)

1. If no name given: list all packages in .token_archive/ and return
2. Check .token_archive/<name>/ exists → error if not
3. Re-import the archived package via import_token()
4. Remove the archive directory on success
```

---

## 7. Safety System

### 7.1 Iteration Limit

| Threshold | Action |
|-----------|--------|
| 50 iterations | Pause. Show intermediate state. Ask: "Continue for 50 more?" |
| 100 iterations | Pause again. Warn: "This is unusual." |
| 200 iterations (hard limit) | Force stop. Log as error. Show final state. |

### 7.2 First-Time Command Approval

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

### 7.3 Destructive / Download / Upload Commands

- Tokens flagged as `destructive`, `downloads`, or `uploads` in the registry **always** require approval, every single time
- The approval prompt must clearly state what the command will do
- A predefined blocklist of destructive patterns is maintained in config (rm, git clean, git reset, format, shutdown, etc.)
- During learn mode, if the handler code contains any destructive pattern, auto-flag the token

### 7.4 Community Import Safety

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

## 8. Logging System

### 8.1 Schema (SQLite: `logs.db`)

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

### 8.2 Retention Policy

- **Prompts table:** Keep all entries forever (input + final output is small)
- **Iterations table:** Keep detailed iteration chains for the **100 most recent prompts**. Prune older iteration data on each new prompt (keep the prompt row, delete its iterations)
- **Learning events:** Keep forever (these are rare and important)
- **Execution log:** Keep forever (critical audit trail — every shell command, file operation, download/upload, and connection opened)

### 8.3 Log Access Commands

In the REPL:
- `logs recent` — last 20 prompts with their results
- `logs trace <n>` — full iteration trace for prompt #n (if retained)
- `logs learned` — all learning events
- `logs search <query>` — search prompts by text
- `logs exec` — recent execution log (shell commands, file ops, network activity)
- `logs exec <n>` — execution log entries for prompt #n

---

## 9. Build System

### 9.1 `setup.sh` (1st Build → Workshop Mode)

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

### 9.2 `build.sh` (2nd Build → Hardened Mode)

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

## 10. Community Token Sharing

### 10.1 Token Package Format

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

### 10.2 Import Flow

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

### 10.3 Export Flow

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

## 11. Open Concerns

### 11.1 Token Interaction Complexity — RESOLVED
As tokens grow, interactions become combinatorial. "5 minus 3 plus 2" — is it `(5-3)+2` or `5-(3+2)`? Priority handles `multiply vs add` but same-priority tokens need position-based (left-to-right) resolution.

**Resolution:** Handlers are designed to handle all possible phrase combinations. The LLM generates all common phrase patterns during learn mode, and each pattern becomes a test case with expected output. Since we have function + input + output for every case, testing covers this comprehensively. Left-to-right processing for same-priority tokens is the rule.

### 11.2 LLM Code Generation Quality — RESOLVED
The learn mode depends on an external LLM producing correct handler code. If the LLM generates buggy code, the user must either debug it manually or re-prompt.

**Resolution:** User-driven retry. If generated code fails tests or looks wrong, user decides whether to re-prompt the LLM with feedback or manually edit. Details to be fleshed out during learn mode implementation.

### 11.3 Ambiguous Handler Boundaries — RESOLVED
If a sentence is: "play something and say hello" — `play`'s handler needs to know that "say hello" belongs to a different token. This is the old CLINT `segregate()` problem.

**Resolution:** `find_token_boundary()` in `src/engine/tokenizer.py`. Instead of loading all tokens from the DB into memory and scanning against them, the function iterates over the words in the current text (the prompt fragment) and checks each word against the registry. Since prompts are short (few words) but the token DB can grow large, this is the more scalable direction — O(words_in_prompt) DB lookups rather than O(all_tokens) in memory. Handlers call `find_token_boundary(text, exclude_keywords)` to find where the next token starts and stop consuming operands at that position. Matches the legacy CLINT `segregate()` approach, modernized.

### 11.4 Security of Executed Code — RESOLVED
Even with subprocess isolation, a handler can still make network calls, read files, etc. within its subprocess. True sandboxing (seccomp, containers) would be heavier.

**Resolution:** Security is ultimately dependent on user monitoring. The standard version provides pragmatic safety: subprocess isolation, static analysis flagging, approval gates, and timeouts. This is sufficient — the user reviews all code before it runs, and destructive/network operations always require explicit approval.

### 11.5 External LLM Dependency — DEFERRED
Learn mode requires an external LLM. The tool itself (outside learn mode) works fully offline.

**Current thinking:** Instead of baking in API calls, learn mode may simply open the user's code editor with a pre-crafted prompt that the user can feed to their own AI tool (Copilot, Claude Code, ChatGPT, etc.). This means: no API key management in our tool, no provider lock-in, no network dependency in our codebase. The user handles the LLM interaction in whatever way they prefer, and pastes back / saves the result. To be finalized when we implement learn mode.

### 11.6 What AI Provider / Model to Target? — DEFERRED
Tied to 11.5. If we go with the "open editor with prompt" approach, this becomes a non-issue — the user picks their own AI tool. If we later add direct API integration, it will be configurable. Decision deferred to learn mode implementation phase.

---

## 12. Decision Summary & Your Calls

| # | Decision | My Recommendation | Status |
|---|----------|-------------------|--------|
| 1 | TUI vs CLI | CLI with `rich` | **Approved** |
| 2 | Log DB | SQLite | **Approved** |
| 3 | Token registry DB | SQLite + .py handler files | **Approved** |
| 4 | Programming language | Python | **Approved** |
| 5 | Build script names | `setup.sh` / `build.sh` | **Approved** |
| 6 | Mode names | Workshop / Hardened | **Approved** |
| 7 | Handler execution model | Subprocess isolation (safe) with opt-in direct import (fast) | **Approved** |
| 8 | LLM provider(s) | User handles it (open editor with prompt) | **Deferred to learn mode phase** |
| 9 | Minimum Python version | 3.10 (match/case, modern typing) | **Approved** |
| 10 | External dependencies | `rich` only (everything else stdlib) | **Approved** |

### 12.1 Resolved: 2nd Mode Name

**Hardened Mode** — locked down, no modifications, security-first connotation. Workshop is where you craft; Hardened is the finished, tamper-proof result.

---

## 13. Implementation Plan

Build in stages. No stage begins until the previous is complete and approved.

### Stage 1 — Core Engine (Workshop Mode foundation)

| Order | Component | What Gets Built |
|-------|-----------|----------------|
| 1 | `setup.sh` | Python version check, venv creation, pip install, DB init, directory scaffolding, alias suggestion |
| 2 | `requirements.txt` | Pinned + hashed dependencies (`rich`) |
| 3 | `src/main.py` | REPL loop, input routing, mode detection |
| 4 | `src/engine/` | `processor.py` (reduction loop), `tokenizer.py` (token identification), `resolver.py` (alias resolution, priority ordering) |
| 5 | `src/registry/` | `store.py` (SQLite CRUD for tokens/aliases/tests), `loader.py` (dynamic handler loading), `schema.sql` |
| 6 | `src/cinnamonint_logging/` | `logger.py` (prompt/result logging), `iterations.py` (per-prompt iteration chains), `schema.sql` |
| 7 | `db/` | Initialize `registry.db` and `logs.db` with schemas |
| 8 | `tokens/` | Directory structure + manually ported handlers from legacy CLINT (plus, minus, add, subtract, multiply, divide, say, exit, etc.) |
| 9 | `tests/` | Test suites for all ported handlers |

**Exit criteria:** User can run `setup.sh`, launch the REPL, type sentences, and get correct results from ported handlers. All iterations are logged. All tests pass.

### Stage 2 — Safety & Community

| Order | Component | What Gets Built |
|-------|-----------|----------------|
| 1 | `src/safety/approvals.py` | Command variation approval system (hash-based, per-variation) |
| 2 | `src/safety/limits.py` | Iteration limits (50/100/200 thresholds) |
| 3 | `src/safety/sandbox.py` | Static analysis via `ast.parse()`, suspicious pattern detection |
| 4 | `src/community/importer.py` | Download + review + install tokens from local path |
| 5 | `src/community/exporter.py` | Package tokens for sharing (manifest.cinnamonint.json + handler.cinnamonint.py + test.cinnamonint.py) |
| 6 | `src/community/forget.py` | Remove imported tokens with archive for recovery |
| 7 | `src/community/restore.py` | Re-import forgotten tokens from archive |

**Exit criteria:** Approval prompts work for new command variations. Destructive commands always prompt. Import/export of token packages works with full code review and test verification.

### Stage 3 — Config, Learn Mode & LLM Integration

| Order | Component | What Gets Built |
|-------|-----------|----------------|
| 1 | `src/config/settings.py` | Configuration management (paths, flags, limits) |
| 2 | `skills/learn.skills.md` | Comprehensive instructions for AI-assisted code generation — handler contract, naming conventions, `extract_operands` usage, test structure, examples |
| 3 | `src/learn/learner.py` | Learn mode orchestration — check existence, open VS Code, copy prompt to clipboard, wait for files, validate, test, register |
| 4 | `src/learn/tester.py` | Test runner for generated handlers — run new handler tests + full regression suite |
| 5 | Safety updates | Update `sandbox.py` for learn mode (auto-flag destructive patterns in generated code) |
| 6 | Dispatch wiring | Replace the "not yet implemented" stub in `dispatch.py` with actual learn mode routing |

**Exit criteria:** User can type `learn <word>`, VS Code opens, prompt is copied to clipboard referencing `skills/learn.skills.md`. User generates handler + tests via their AI tool, returns to REPL, system validates, runs tests, and registers the token. `forget <word>` works.

### Stage 4 — Spell Correction & Subprocess Isolation

| Order | Component | What Gets Built |
|-------|-----------|----------------|
| 1 | Port legacy handlers | Manually write handlers for remaining legacy CLINT commands (intro, wait, timer, vatican cameos, etc.) and their test suites |
| 2 | `src/engine/spellcheck.py` | Pre-processing spell correction — `difflib.get_close_matches()` against tokens/aliases + bundled `words.txt` dictionary. Interactive prompts ("Did you mean 'subtract'?"). Numbers/punctuation skipped. Never silent autocorrect. |
| 3 | `words.txt` | Bundled English word list (~100k words, public domain). Loaded into a `set()` at startup. |
| 4 | `src/registry/loader.py` | Subprocess handler isolation — default safe mode runs handlers via `subprocess` with configurable timeout (`HANDLER_TIMEOUT_SECONDS`). Opt-in "unsafe fast mode" in Workshop uses `importlib` direct import. |
| 5 | Tests | Test suites for spell correction, subprocess execution model, and ported legacy handlers. |

**Exit criteria:** All remaining legacy CLINT handlers are ported with tests. Misspelled tokens are caught before the reduction loop and the user is prompted interactively. Handlers execute in subprocess by default with timeout enforcement. Direct import available as opt-in fast mode. All existing tests still pass.

### Stage 5 — Hardened Mode

| Order | Component | What Gets Built |
|-------|-----------|----------------|
| 1 | `build.sh` | Test runner, file copier, DB cloner, permission setter, runner script generator |
| 2 | `dist/` | Generated output directory with read-only registry, writable logs, runner script |

**Exit criteria:** `build.sh` produces a `dist/` folder. Hardened mode runs correctly, rejects learn/import/forget commands, and all logging works.

---

## 14. Coding Standards

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

---

## 15. Implementation Deviations

Deviations from the original design recorded during implementation.

### 15.1 `src/logging/` renamed to `src/cinnamonint_logging/`

**Stage:** 1 — Core Engine
**Reason:** Python's `src/logging/__init__.py` shadows the stdlib `logging` module. When `rich` (our only external dependency) tries to `from logging import getLogger`, Python resolves it to our package instead of stdlib, causing an `ImportError`. Renaming to `cinnamonint_logging/` eliminates the conflict while keeping the module purpose clear. All internal imports updated accordingly.

### 15.2 `find_token_boundary()` applied to all multi-number token handlers

**Stage:** 1 — Core Engine
**Reason:** Handlers with "consume all numbers" paths (`multiply`, `divide`, `add`) greedily consumed operands past token keyword boundaries. For example, `multiply 2 2 and 4 divide by 8` produced `128 divide by 8` instead of `16 divide by 8` because `multiply` consumed the `8` that belonged to `divide`. Fix: all multi-number handlers now call `find_token_boundary()` from `src/engine/tokenizer.py` to limit their operand scanning to the region before the next known token. Binary handlers (`minus`, `subtract`, `into`, `by`) only take one number from each side so they naturally respect boundaries. `plus` was additionally fixed to use only the last left number (consistent with `minus`) instead of summing all left numbers.

### 15.3 `test_cases` table dropped — test files are the single source of truth

**Stage:** 2 — Safety & Community
**Reason:** The original design stored test cases in a `test_cases` SQLite table. In practice, seeded tokens had tests in both the DB and as `.py` files, while imported tokens only had `.py` files. The DB entries were dead data — pytest ran the `.py` files directly, never the DB rows. Maintaining two sources of truth added complexity with no benefit. Resolution: dropped the `test_cases` table entirely, added a `test_path TEXT` column to the `tokens` table pointing to the test `.py` file (e.g., `tests/math/test_plus.py`). Both seeded and imported tokens now follow the same pattern: test files are the only source of truth, and the DB just tracks where they live.

### 15.4 Seeded tokens are unforgettable

**Stage:** 2 — Safety & Community
**Reason:** The original §6.3 allowed forgetting any token. During implementation, the decision was made that seeded tokens — the built-in tokens registered by `seed.py` — should not be forgettable. They form the baseline vocabulary. If a user wants to remove a seeded token, they must re-seed manually (delete the DB, re-run seed). The forget command checks `source == 'seed'` and blocks with an informational message.

### 15.5 Forget archives via export, restore re-imports

**Stage:** 2 — Safety & Community
**Reason:** The original §6.3 suggested moving the handler `.py` to a trash folder. The implementation instead exports the full token package (manifest + handler + test file) to `.token_archive/` using the same `export_token()` function used for sharing. This means archived tokens are complete, self-contained packages in the standard cinnamonint format. Recovery is handled by a `restore` command that simply re-imports the archived package via `import_token()` and removes the archive on success.

### 15.6 Package files use `.cinnamonint` infix naming

**Stage:** 2 — Safety & Community
**Reason:** The original §10.1 used generic names (`manifest.json`, `handler.py`, `tests.json`). The implementation uses `.cinnamonint` infixed names (`manifest.cinnamonint.json`, `handler.cinnamonint.py`, `test.cinnamonint.py`) to avoid collisions with other files in a directory and to make cinnamonint packages instantly recognizable. The test file was also changed from JSON (`tests.json` / `tests.cinnamonint.json`) to a Python file (`test.cinnamonint.py`) — since test files are actual pytest suites, shipping them as `.py` preserves them exactly as-is without a lossy JSON→Python conversion step.

### 15.7 `source` column replaces `author`-based seeded detection

**Stage:** 2 — Safety & Community
**Reason:** The original implementation used `author == 'local'` to identify seeded tokens. This conflated "who wrote it" with "how it entered the system." Once learn mode lands (Stage 3), locally learned tokens would also have `author = 'local'` but should be forgettable. Resolution: added a `source TEXT DEFAULT 'seed'` column to the `tokens` table with three values: `'seed'` (built-in via `seed.py`), `'learn'` (taught via learn mode), `'import'` (imported from a package). The `author` field remains purely informational. The forget guard now checks `source == 'seed'`.
