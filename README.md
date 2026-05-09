# Cinnamonint

A deterministic, iterative sentence-reduction engine in Python. Users type natural-language sentences; the engine identifies registered token keywords, calls their handlers to transform the sentence, and loops until no tokens remain.

No neural networks. No training data. No hallucinations. Just explicit, auditable, one-word-at-a-time intelligence.

> For the origin story, philosophy, and FAQs, see [Based README.md](based_README.md).

---

## Table of Contents

- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Sentence Processing](#sentence-processing)
  - [REPL Commands](#repl-commands)
  - [Piped Input](#piped-input)
- [Registered Tokens](#registered-tokens)
- [Features](#features)
  - [Iterative Reduction Engine](#iterative-reduction-engine)
  - [Spell Correction](#spell-correction)
  - [Subprocess Isolation](#subprocess-isolation)
  - [Safety System](#safety-system)
  - [Logging](#logging)
  - [Learn Mode](#learn-mode)
  - [Community Sharing](#community-sharing)
  - [User Dictionary](#user-dictionary)
  - [Hardened Mode](#hardened-mode)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [Requirements](#requirements)
- [Contributing](#contributing)

---

## How It Works

Every sentence is processed through an **iterative reduction loop**:

1. The engine scans the sentence for registered keywords (tokens).
2. The leftmost (or highest-priority) token is selected.
3. The token's handler function receives the sentence, processes its portion, and returns the transformed sentence.
4. The engine loops back to step 1 with the new sentence.
5. When no tokens remain, the final sentence is the output.

```
Input:  "Add 5, 6 and 7 and subtract 11"
  → add(5, 6, 7) → "18 and subtract 11"
  → and()        → "18 subtract 11"
  → subtract()   → "7"
Output: "7"
```

Each token is a self-contained Python module with a `handle(sentence)` function. The engine never executes handler code directly in the main process — handlers run in isolated subprocesses by default.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/SayadPervez/Cinnamonint.git
cd Cinnamonint

# Run setup (creates venv, installs deps, initializes DBs, seeds tokens)
./setup.sh

# Launch the REPL
./cinnamonint
```

### What setup.sh does

1. Checks for Python 3.10+
2. Creates a `.venv` virtual environment
3. Installs dependencies (`rich` + dev tools)
4. Creates the `db/`, `tokens/`, `tests/` directories
5. Initializes `registry.db` (token registry) and `logs.db` (prompt history)
6. Seeds all built-in tokens into the registry
7. Optionally downloads an English dictionary for enhanced spell correction
8. Makes the `./cinnamonint` entry point executable

---

## Usage

### Sentence Processing

```
>>> 5 plus 3
8

>>> 10 minus 4 plus 2
8

>>> say hello world
hello world

>>> hi
Hey there! 👋

>>> wait 3 seconds and ping me
3...2...1... BEEP

>>> time
14:32:05

>>> 2 multiply by 3 plus 1
7
```

Tokens are processed iteratively. Chained operations reduce left-to-right (respecting priority), so `2 multiply by 3 plus 1` first resolves `multiply` (priority 3) → `6 plus 1`, then `plus` (priority 2) → `7`.

### REPL Commands

| Command | Description |
|---------|-------------|
| `exit` / `quit` / `q` | Exit the REPL |
| `logs recent` | Show last 20 prompts |
| `logs trace <id>` | Show iteration-by-iteration trace for a prompt |
| `logs learned` | List all learning events |
| `logs search <query>` | Search prompt history by text |
| `logs exec` | Recent execution log |
| `logs exec <id>` | Execution log for a specific prompt |
| `dictionary` | List ignored words and remembered corrections |
| `dictionary remove <word>` | Remove a word from ignored list or corrections |
| `learn <word>` | Start the learn flow to teach a new token |
| `forget <token>` | Archive and remove a token |
| `restore` | List archived (recoverable) tokens |
| `restore <token>` | Re-import a previously forgotten token |
| `export <token>` | Package a token for sharing |
| `import <path>` | Import a community token package |

### Piped Input

```bash
echo "5 plus 3" | ./cinnamonint
# Output: 8

echo -e "5 plus 3\n10 minus 3" | ./cinnamonint
# Output:
# 8
# 7
```

Piped input processes each line independently. Spell correction and interactive prompts are disabled in non-interactive mode.

---

## Registered Tokens

### Math

| Token | Aliases | Description |
|-------|---------|-------------|
| `add` | — | Add numbers: `add 5 6 7` → `18` |
| `plus` | `+` | Infix addition: `5 plus 3` → `8` |
| `subtract` | — | Subtract numbers: `subtract 3 from 10` → `7` |
| `minus` | — | Infix subtraction: `10 minus 3` → `7` |
| `multiply` | `multiplied` | Multiply: `3 multiply by 4` → `12` |
| `by` | — | Infix multiplier: `3 by 4` → `12` |
| `divide` | — | Division: `divide 10 by 2` → `5` |
| `into` | — | Infix division: `10 into 2` → `5` |

### System

| Token | Aliases | Description |
|-------|---------|-------------|
| `say` | `speak`, `tell` | Echo text after keyword: `say hello` → `hello` |
| `hi` | `hey`, `hello`, `howdy`, `greetings`, `sup`, `hey there` | Random greeting response |
| `clear` | `cls`, `clrscr` | Clear the terminal screen |
| `exit` | `quit`, `q` | Exit the REPL |

### Utility

| Token | Aliases | Description |
|-------|---------|-------------|
| `wait` | `pause` | Pause with countdown: `wait 5 seconds`, `wait 1 minute and 30 seconds`, `wait 2 and a half minutes` |
| `now` | — | Current time: `now` → `14:32:05` |
| `time` | — | Current time |
| `date` | `today` | Current date |

---

## Features

### Iterative Reduction Engine

The core loop in `src/engine/processor.py`:

- **Tokenizer** scans the sentence for registered keywords, handling punctuation stripping and multi-word tokens.
- **Resolver** picks the next token to process based on position and priority.
- **Processor** calls the handler, replaces the token portion with the result, and loops.
- **Iteration limits** prevent infinite loops:
  - **50 iterations**: Pause and ask to continue
  - **100 iterations**: Warning + pause
  - **200 iterations**: Hard stop

### Spell Correction

Pre-processing step before the reduction loop (`src/engine/spellcheck.py`):

- Checks each word against registered tokens, an English dictionary (if available), and the user dictionary.
- Suggests corrections using `difflib.get_close_matches` (threshold: 0.7).
- Never autocorrects — always prompts interactively.
- Options per suggestion: accept, accept & remember, skip, skip always (add to user dictionary).
- Remembered corrections apply automatically on future inputs.
- Punctuation is stripped before lookups so `"plus,"` still matches `plus`.

**Two modes:**
- **Token-only** (default): Suggests corrections only against registered token names/aliases.
- **Full** (with `data/words.txt`): Also checks against English dictionary — flags truly unknown words.

### Subprocess Isolation

Handlers execute in isolated subprocesses by default (`src/registry/loader.py`):

- The handler's `print()` output is redirected to stderr during execution so it doesn't contaminate the return value.
- Each handler gets a **5-second timeout** (configurable). Timeout-exempt handlers (e.g., `wait`) are whitelisted.
- Live-output handlers (e.g., `wait` countdown) inherit the parent's stderr for real-time display.
- Can be switched to direct execution via `HANDLER_EXECUTION_MODE = "direct"` in settings.

### Safety System

Three layers of protection:

1. **Static Analysis** (`src/safety/sandbox.py`): AST-walks handler source code looking for suspicious patterns — shell execution, file deletion, network calls, `exec()`/`eval()`, environment variable access. Findings are highlighted during code review (learn/import), not silently ignored.

2. **Approval System** (`src/safety/approvals.py`): Tracks which `(token, command_variation)` pairs the user has approved. Destructive/download/upload tokens require approval every time. Normal tokens are approved once per variation and remembered.

3. **Destructive Pattern Detection**: Handler source code is checked against a configurable list of dangerous strings (`rm -rf`, `shutdown`, `dd if=`, etc.).

### Logging

All prompt processing is recorded in `db/logs.db` (`src/cinnamonint_logging/`):

- **Prompt log**: Input text, final output, iteration count, status, timestamp.
- **Iteration trace**: Per-iteration snapshots — sentence before/after, which token processed, duration in ms.
- **Learning events**: Token learned/forgotten/imported/restored with timestamps.
- **Execution log**: Commands run, exit codes, paths accessed.
- **Retention**: Old iteration data is pruned to keep the last 100 entries.

Query logs via the `logs` command in the REPL.

### Learn Mode

AI-assisted token creation (`src/learn/learner.py`):

1. Type `learn <word>` in the REPL.
2. A structured prompt is generated and copied to your clipboard.
3. The REPL commits current state, writes a handover file, and opens your editor (VS Code by default).
4. Paste the prompt into your AI agent. It generates the handler (`tokens/<category>/<word>.py`) and tests (`tests/<category>/test_<word>.py`).
5. Return to the REPL — it detects the handover, runs all tests, and if they pass, registers the token.
6. If tests fail, you can reopen the editor or revert to the pre-learn commit.

The prompt template includes full handler conventions, the project's coding standards, and examples — all from `skills/learn.skills.md`.

### Community Sharing

Tokens can be packaged, shared, and imported (`src/community/`):

**Export** (`export <token>`):
```
exports/<token_name>/
    manifest.cinnamonint.json   — metadata (name, aliases, category, flags)
    handler.cinnamonint.py      — handler source code
    test.cinnamonint.py         — test file
```

**Import** (`import <path>`):
- Reads the manifest, runs static analysis, shows code for review.
- Runs the token's tests before registering.
- Supports single package import or bulk import from a directory.

**Forget** (`forget <token>`):
- Archives the token package to `.token_archive/` before removing it.
- Seeded tokens (built-in) are protected and cannot be forgotten.

**Restore** (`restore <token>`):
- Re-imports from `.token_archive/` — full round-trip recovery.

### User Dictionary

Persistent per-user word list (`data/user_dictionary.json`) and corrections (`data/corrections.json`):

- **Ignored words**: Words the user has told the spell checker to skip permanently.
- **Remembered corrections**: Typo → correction mappings applied automatically.
- Managed via the `dictionary` REPL command.

### Hardened Mode

A locked-down distribution for deployment (`build.sh`):

```bash
./build.sh    # runs tests → produces dist/
```

**What it does:**
- Runs the full test suite — aborts if any test fails.
- Copies `src/`, `tokens/`, `data/`, `.venv/` into `dist/`.
- Clones `registry.db` as **read-only** (chmod 444).
- Creates a fresh writable `logs.db`.
- Generates `dist/cinnamonint` runner script.

**Hardened mode behavior:**
- `learn`, `forget`, `import`, `restore` are blocked with an informative message.
- Sentence processing, logging, dictionary, and export still work normally.
- Mode is auto-detected by checking if `registry.db` is writable.
- The `dist/` folder is self-contained and relocatable (same machine).

```bash
# copy anywhere and alias
cp -r dist/ ~/cinnamonint
alias cinnamonint="$HOME/cinnamonint/cinnamonint"
```

---

## Project Structure

```
cinnamonint/
├── src/
│   ├── main.py                  # REPL entry point
│   ├── seed.py                  # Built-in token seeding (DO NOT EDIT)
│   ├── config/
│   │   └── settings.py          # Paths, flags, limits, mode detection
│   ├── engine/
│   │   ├── processor.py         # Iterative reduction loop
│   │   ├── tokenizer.py         # Token identification in sentences
│   │   ├── resolver.py          # Token selection (position + priority)
│   │   ├── spellcheck.py        # Pre-processing spell correction
│   │   └── user_dictionary.py   # User word list (JSON read/write)
│   ├── registry/
│   │   ├── store.py             # SQLite CRUD for tokens/aliases
│   │   ├── loader.py            # Handler loading + subprocess execution
│   │   └── schema.sql           # Registry DB schema
│   ├── commands/
│   │   ├── dispatch.py          # REPL command routing + hardened gating
│   │   ├── logs.py              # Log query commands
│   │   └── dictionary.py        # Dictionary management commands
│   ├── learn/
│   │   ├── learner.py           # Learn mode orchestrator
│   │   ├── tester.py            # Test runner for learn flow
│   │   └── test_setup.py        # Test file scaffolding
│   ├── community/
│   │   ├── exporter.py          # Token packaging for sharing
│   │   ├── importer.py          # Token import with safety review
│   │   ├── forget.py            # Token archival + removal
│   │   └── restore.py           # Token recovery from archive
│   ├── safety/
│   │   ├── sandbox.py           # AST-based static analysis
│   │   ├── approvals.py         # Command variation approval tracking
│   │   └── limits.py            # Iteration threshold management
│   └── cinnamonint_logging/
│       ├── logger.py            # Prompt + event logging
│       ├── iterations.py        # Per-iteration trace logging
│       └── schema.sql           # Logs DB schema
├── tokens/                      # Handler .py files by category
│   ├── math/                    #   add, plus, subtract, minus, multiply, by, divide, into
│   ├── system/                  #   say, hi, clear, exit
│   └── utility/                 #   wait, now, time, date
├── tests/                       # pytest suites mirroring token categories
├── db/                          # SQLite databases (registry.db, logs.db)
├── data/                        # Dictionaries, corrections, user dictionary
├── exports/                     # Exported token packages
├── skills/                      # AI instruction files for learn mode
├── legacy/                      # Original CLINT source (reference only)
├── setup.sh                     # Workshop mode setup (1st build)
├── build.sh                     # Hardened mode build (2nd build)
└── cinnamonint                  # Entry point script
```

---

## Configuration

All configuration lives in `src/config/settings.py`. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `HANDLER_EXECUTION_MODE` | `"subprocess"` | `"subprocess"` (isolated) or `"direct"` (in-process) |
| `HANDLER_TIMEOUT_SECONDS` | `5` | Subprocess timeout per handler call |
| `SOFT_ITERATION_LIMIT` | `50` | Iterations before first pause-and-ask |
| `WARN_ITERATION_LIMIT` | `100` | Iterations before warning |
| `HARD_ITERATION_LIMIT` | `200` | Unconditional stop |
| `ITERATION_RETENTION_COUNT` | `100` | How many iteration traces to keep |
| `WORD_LOOKUP_THRESHOLD` | `250` | Max words for per-word DB lookup (vs. fetch-all) |
| `CINNAMONINT_EDITOR` | `code` | Editor opened during learn mode (env var) |

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific category
python -m pytest tests/math/ -v
python -m pytest tests/system/ -v
python -m pytest tests/engine/ -v
python -m pytest tests/safety/ -v
python -m pytest tests/community/ -v

# Run a specific test file
python -m pytest tests/utility/test_wait.py -v
```

Tests use `unittest.TestCase` with `snake_case` class names. Handler tests import the handler directly; engine tests run through the full reduction loop. The test suite uses a separate `test_registry.db` (via `CINNAMONINT_TEST_DB=1` environment variable) to avoid touching production data.

**Current test count: 316 tests.**

---

## Requirements

- **Python 3.10+** (uses `match`/`case` and modern typing)
- **Rich** — the sole external runtime dependency (console output, syntax highlighting, tables)
- **pytest** — dev dependency for testing

No `requests`, no `numpy`, no heavyweight packages. stdlib + Rich only.

---

## Contributing

Contributions are welcome. Please read [based_README.md](based_README.md) to understand the philosophy and core idea behind this project before submitting changes.

### Coding Standards

| Element | Convention | Example |
|---------|-----------|--------|
| Variables | `snake_case` | `token_name`, `handler_path` |
| Functions | `snake_case` | `load_handler()`, `run_tests()` |
| Classes | `snake_case` | `token_store` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_ITERATIONS`, `DB_PATH` |
| Files/dirs | `snake_case` | `processor.py`, `src/engine/` |

**No PascalCase or camelCase anywhere** — not in variables, functions, classes, files, or directories.

Additional rules:
- **DRY** — if logic appears 2+ times, extract into a function.
- **Readable parent functions** — top-level functions should read as a sequence of named calls, not inline logic.
- **No global mutable state** — pass dependencies explicitly.
- **Classes for state, functions for stateless ops.**
- **Minimal dependencies** — keep the dependency tree as small as possible to reduce supply chain attack surface. No unnecessary packages.

### AI Assistance Policy

This project was written with the help of AI (Claude). AI-assisted pull requests are accepted and encouraged — but:

1. **You must manually review the code you submit.** AI-generated code that is clearly unreviewed (nonsensical variable names, dead code, hallucinated imports) will be rejected.
2. Approximately 75% of the existing codebase has been manually reviewed by the maintainer. The same standard applies to contributions.
3. If your PR introduces a new token, follow the handler structure defined in `skills/learn.skills.md`.

### Pull Request Guidelines

- All tests must pass (`python -m pytest tests/`). PRs that break existing tests will not be merged.
- New tokens must include a test file in `tests/<category>/test_<word>.py`.
- Do not edit `src/seed.py` or `db/registry.db` directly.
- Do not commit `.learn_handover.json`, `__pycache__/`, or `dist/`.

### Review Turnaround

The maintainer is employed full-time. Pull requests are reviewed manually and with AI assistance, typically on **weekends only**. Please be patient — your contribution is appreciated.

### Getting Started

```bash
# fork + clone
git clone https://github.com/<you>/Cinnamonint.git
cd Cinnamonint
./setup.sh

# make changes, then run tests
python -m pytest tests/ -v

# submit PR against main branch
```
