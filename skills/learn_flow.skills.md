# Learn Mode — Complete Flow Map

> Reference document for `src/learn/learner.py` implementation.

---

## State File

`.learn_handover.json` at project root. Created on handover, deleted on completion.
**Must be listed in `.gitignore`** — it is control state, not project content.

```json
{
  "word": "subtract",
  "commit_hash": "a1b2c3d",
  "timestamp": "2026-03-18T22:15:00"
}
```

---

## Handler METADATA Constant

Every generated handler must include a `METADATA` dict constant. The learner
reads this to register the token in the DB. `skills/learn.skills.md` enforces
this structure. If `METADATA` is missing or malformed, registration fails.

```python
METADATA = {
    "name": "subtract",
    "aliases": ["minus", "take away"],
    "category": "math",
    "priority": 2,
    "destructive": False,
    "downloads": False,
    "uploads": False,
}
```

---

## Flow Tree

```
USER TYPES: learn <word>
│
├── Pending handover exists (.learn_handover.json)?
│   └── YES → Print error: "You have a pending learn session
│              for '<prev_word>'. Complete it first." → STOP
│
├── Token already exists in registry?
│   └── YES → Print error: "<word> is already a registered token." → STOP
│
├── Working tree dirty? (uncommitted changes)
│   └── YES → Print error: "You have uncommitted changes.
│              Commit or stash before learning." → STOP
│
└── ALL CLEAR → Continue
    │
    ├─ 1. Generate prompt template string
    │     "refer the skills/learn.skills.md file to understand what and
    │      what not is required. generate handler and tests for <word>."
    │
    ├─ 2. Copy prompt to system clipboard
    │     (fallback: if clipboard tools unavailable, print prompt
    │      to terminal so user can copy manually)
    │
    ├─ 3. Print:
    │     "Prompt template generated and copied to clipboard.
    │      Opening your fav IDE. Paste the prompt to your
    │      agent and come back to continue."
    │
    ├─ 4. git add -A && git commit -m "learn: <word>. handover initiated"
    │
    ├─ 5. Store handover state to .learn_handover.json:
    │     { word, commit_hash (from step 4), timestamp }
    │
    ├─ 6. Wait 3 seconds
    │
    ├─ 7. Open VS Code (code <project_root>)
    │
    └─ 8. Exit REPL
```

---

```
USER REOPENS CINNAMONINT (handover state detected in .learn_handover.json)
│
├── Print: "Hope you have created and implemented <word>.
│           Shall we continue with testing your addition? (y/n)"
│
│
├── USER SAYS: YES
│   │
│   ├── Verify expected files exist:
│   │   ├── Handler: tokens/<category>/<word>.py  (category from METADATA)
│   │   ├── Tests:   tests/<category>/test_<word>.py
│   │   └── MISSING → Print error listing missing files
│   │       ├── Ask: "Open IDE to create them? (y/n)"
│   │       ├── YES → Open VS Code, exit (handover persists)
│   │       └── NO  → revert flow (same as tests-fail-no-fix below)
│   │
│   ├── Parse METADATA constant from handler file
│   │   └── MISSING/MALFORMED → Print error, same open-IDE-or-revert fork
│   │
│   ├── Run: pytest (full suite)
│   │
│   ├── TESTS PASS ✓
│   │   ├── git add tokens/ tests/ src/ && git commit -m "learn: <word> successful"
│   │   ├── Register token in registry DB using METADATA dict (source='learn')
│   │   ├── Delete .learn_handover.json
│   │   └── Print: "Token '<word>' learned and registered successfully!"
│   │   └── DONE → enter normal REPL
│   │
│   └── TESTS FAIL ✗
│       ├── Print: "Cannot have a token that fails tests."
│       ├── Show failure summary
│       ├── Ask: "Would you like to open the IDE to fix? (y/n)"
│       │
│       ├── USER SAYS: YES (open IDE)
│       │   ├── Open VS Code
│       │   ├── DO NOT delete .learn_handover.json (handover persists)
│       │   └── Exit REPL (user will return later, same flow repeats)
│       │
│       └── USER SAYS: NO (give up, revert)
│           │
│           ├── Verify stored commit_hash exists in git log
│           │   ├── HASH NOT FOUND
│           │   │   ├── Print error: "Cannot revert — handover commit
│           │   │   │   <hash> not found in git history. Manual
│           │   │   │   cleanup required."
│           │   │   ├── Delete .learn_handover.json
│           │   │   └── DONE → enter normal REPL
│           │   │
│           │   └── HASH FOUND → Continue
│           │
│           ├── git reset --hard <stored_commit_hash>
│           ├── git reset --soft HEAD~1
│           ├── Delete .learn_handover.json
│           ├── Print: "Reverted to state before learning '<word>'."
│           └── DONE → enter normal REPL
│
│
└── USER SAYS: NO
    │
    ├── Ask: "Do you wish to revert to the state before learn? (y/n)"
    │
    ├── USER SAYS: YES (revert)
    │   │
    │   ├── Verify stored commit_hash exists in git log
    │   │   ├── HASH NOT FOUND
    │   │   │   ├── Print error: "Cannot revert — handover commit
    │   │   │   │   <hash> not found in git history. Manual
    │   │   │   │   cleanup required."
    │   │   │   ├── Delete .learn_handover.json
    │   │   │   └── DONE → enter normal REPL
    │   │   │
    │   │   └── HASH FOUND → Continue
    │   │
    │   ├── git reset --hard <stored_commit_hash>
    │   ├── git reset --soft HEAD~1
    │   ├── Delete .learn_handover.json
    │   ├── Print: "Reverted to state before learning '<word>'."
    │   └── DONE → enter normal REPL
    │
    └── USER SAYS: NO (keep as-is)
        ├── Delete .learn_handover.json
        ├── Print: "Keeping current state as-is."
        └── DONE → enter normal REPL
```

---

## Git State Diagram

```
            learn <word>                      User works
STATE A ──────────────────► STATE B ─ ─ ─ ─ ─ ─ ─ ─ ► STATE C
(before learn)           (handover commit)         (user's changes,
                          hash stored in             possibly more
                          .learn_handover.json)      commits)


REVERT OPERATION (from any state after B):
  1. git reset --hard <stored_hash>    →  goes to STATE B
  2. git reset --soft HEAD~1           →  HEAD at STATE A,
                                          handover changes staged
                                          (not committed)

SUCCESS OPERATION (from STATE C):
  1. git add tokens/ tests/ src/
  2. git commit -m "learn: <word> successful"
  3. parse METADATA from handler, register token in DB
                                        →  STATE D (complete)
```

---

## Pre-Handover Guards

1. **Pending handover** — refuse if `.learn_handover.json` already exists
2. **Token collision** — refuse if the word is already registered
3. **Dirty tree** — refuse if there are uncommitted changes (`git status --porcelain` non-empty)

---

## Return Guards

1. **File existence** — verify handler `.py` and test `.py` exist at expected paths before running tests
2. **METADATA constant** — parse the handler file, extract the `METADATA` dict. Fail if missing or malformed (missing required keys: name, category, priority, aliases, destructive, downloads, uploads)
3. **Clipboard fallback** — if `xclip`/`xsel`/`wl-copy` unavailable during handover, print prompt to terminal instead

---

## Revert Safety Rules

1. **Store the exact commit hash** of the "handover initiated" commit — never rely on commit messages or relative refs like `HEAD~1`
2. **Before any reset**, verify the stored hash exists: `git cat-file -t <hash>` must return `commit`
3. **If hash not found** → refuse to revert, print error, clear handover state. The user may have rebased, squashed, or garbage-collected. Manual cleanup is their responsibility
4. **Never revert without the stored hash** — no guessing, no searching by message
5. **User may have made manual commits** between handover and return — the hard reset to the stored hash wipes those too (this is intentional and the user is warned)
6. **Scoped commits** — success commit uses `git add tokens/ tests/ src/` (not `-A`) to avoid bundling unrelated changes

---

## Terminal Paths Summary

| Path | Steps | Git outcome | Handover cleared? |
|------|-------|-------------|-------------------|
| YES → tests pass | commit success | State A → B → C → D | Yes |
| YES → tests fail → open IDE | reopen VS Code, exit | stays at C | **No** (loop) |
| YES → tests fail → no fix | hard reset + soft reset | back to A (staged) | Yes |
| NO → revert | hard reset + soft reset | back to A (staged) | Yes |
| NO → keep | no git action | stays at C | Yes |
| Any → hash not found | no git action | stays wherever it is | Yes |

---

## Implementation Checklist — Stage 3

### New files to create

| # | File | Purpose |
|---|------|---------|
| 1 | `skills/learn.skills.md` | AI instruction file — handler contract, METADATA constant structure, `extract_operands` for flagged tokens, test file conventions, naming standards, example handler + test, do's and don'ts |
| 2 | `src/learn/learner.py` | Learn mode orchestrator — pre-handover guards, clipboard copy, git commit, handover file write, VS Code launch, exit. Return flow: file verification, METADATA parse, pytest run, registration or revert |
| 3 | `src/learn/tester.py` | Test runner — runs `pytest` via subprocess, parses results, returns structured pass/fail |

### Existing files to modify

| # | File | What changes |
|---|------|-------------|
| 4 | `src/config/settings.py` | Add: `LEARN_HANDOVER_FILE`, `EDITOR_COMMAND` (default `"code"`), `LEARN_TEMP_DIR` |
| 5 | `src/commands/dispatch.py` | Replace `"Learn mode is not yet implemented (Stage 3)."` stub with call to `learner.learn()` |
| 6 | `src/main.py` | On startup, check for `.learn_handover.json` — if found, run the return flow before entering normal REPL |
| 7 | `src/safety/sandbox.py` | Wire `analyze_handler_code()` into the learn return flow — auto-flag destructive/downloads/uploads in generated code and cross-check against METADATA flags |
| 8 | `.gitignore` | Add `.learn_handover.json` |

### Summary of touches

```
NEW:
  skills/learn.skills.md          ← AI instructions (the big one)
  src/learn/learner.py            ← orchestrator
  src/learn/tester.py             ← pytest wrapper

MODIFIED:
  src/config/settings.py          ← new constants
  src/commands/dispatch.py        ← wire learn command
  src/main.py                     ← handover return detection
  src/safety/sandbox.py           ← learn-mode auto-flagging
  .gitignore                      ← exclude handover file
```
