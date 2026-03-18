# Cinnamonint — Agent Instructions

Cinnamonint is an iterative sentence-reduction engine in Python. Users type natural-language sentences; the engine identifies registered token keywords, calls their handlers to transform the sentence, and loops until no tokens remain.

## AI Instructions

> **Never start coding without approval. Answer queries first and only then, you code once you have approval.**

## Skill Files

- Refer `skills/learn.skills.md` if you are asked to write handler and test code for a new token.
- Refer `skills/learn_flow.skills.md` for the learn flow (handover, testing, registration, revert).
- Refer `design_doc.md` if you are trying to build this project from scratch or understand architecture.

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `src/` | Source code — engine, registry, learn, safety, logging, community, config |
| `tokens/` | Handler `.py` files organised by category (math/, system/, utility/) |
| `tests/` | pytest suites mirroring token categories |
| `db/` | SQLite databases — `registry.db` (tokens), `logs.db` (history) |
| `exports/` | Exported token packages (manifest + handler + test) |
| `skills/` | AI instruction files for code generation |
| `legacy/` | Original CLINT source (reference only, never modify) |

## Hard Constraints

1. **stdlib + Rich only** — `rich` is the sole external runtime dependency. No `requests`, no other packages.
2. **Python ≥ 3.10** — `match`/`case` and modern typing are used throughout.
3. **Never edit `db/registry.db` directly** — use `src/registry/store.py` functions.
4. **Never edit `src/seed.py`** — seeded tokens are the immutable baseline.
5. **Never delete `.learn_handover.json`** — it tracks active learn sessions; the system manages it.
6. **All paths relative** — resolve from project root at runtime, no hardcoded absolute paths.
7. **Handlers execute in subprocess** — never `exec()`/`eval()` handler code in the main process.
8. **Destructive/download/upload tokens always require approval** — no silent execution.

## Coding Standards

| Element | Convention | Example |
|---------|-----------|---------|
| Variables | `snake_case` | `token_name`, `handler_path` |
| Functions | `snake_case` | `load_handler()`, `run_tests()` |
| Classes | `snake_case` separators | `token_store` — **NO PascalCase** |
| Constants | `UPPER_SNAKE_CASE` | `MAX_ITERATIONS`, `DB_PATH` |
| Files/dirs | `snake_case` | `processor.py`, `src/engine/` |

### Rules

- **No PascalCase or camelCase anywhere** — not in variables, functions, classes, files, or directories.
- **DRY** — if logic appears 2+ times, extract into a function.
- **Readable parent functions** — top-level functions read as a sequence of named calls, not inline logic.
- **No global mutable state** — pass dependencies explicitly.
- **Classes for state, functions for stateless ops.**
