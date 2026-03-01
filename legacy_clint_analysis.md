# CLINT — Command Line Interface NLP Tool

## What Is It?

CLINT is a personal AI assistant built for the Windows command line, inspired by JARVIS from Iron Man. The name says it all: **C**ommand **L**ine **I**nterface **N**LP **T**ool. It takes natural language input ("play despacito", "what's 5 plus 3", "wait for 2 mins then say hello"), figures out what commands are being asked for, and executes them — complete with text-to-speech responses via `pyttsx3`.

The intro speech says it best:

> *"Hey there. Myself CLINT, Command Line Interface NLP Tool. Version 87.3. I was built by Pervez, in order to be a personal assistant, and help him with his projects. JARVIS was the inspiration behind my idea."*

---

## Architecture Overview

CLINT follows a **modular plugin architecture**. The system is split into three layers:

```
┌─────────────────────────────────────────────────┐
│           Main Loop (Drag_On_AI_.py)             │
│  ┌───────────┬────────────┬───────────────────┐  │
│  │Interactive │  Cmd Mode  │   Spexec Mode     │  │
│  │   Mode     │ (registry) │ (raw Python exec) │  │
│  └─────┬─────┴─────┬──────┴───────────────────┘  │
│        │           │                              │
│  ┌─────▼───────────▼──────────────────────────┐   │
│  │   Command Registry (Defined_Modules.txt)   │   │
│  │   Alias System (aka_dictionary.txt)        │   │
│  └─────────────────┬──────────────────────────┘   │
│                    │                              │
│  ┌─────────────────▼──────────────────────────┐   │
│  │   Module Files (Modules/*.py)              │   │
│  │   add, subtract, play, say, timer, etc.    │   │
│  └────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### The Main Loop

The entry point (`Drag_On_Artificial_Intelligence_.py`) runs an infinite loop that:
1. Reads user input
2. Routes to one of three modes based on keywords:
   - **Interactive Mode** — the default, natural language processing path
   - **Command Mode** (`cmd_mode`) — for managing the command registry itself
   - **Spexec Mode** — a raw multi-line Python code executor
   - **Akapi Mode** — for managing command aliases
3. Logs everything to a master file via `readwriter()`

### The Command Registry

Commands are registered in `Defined_Modules.txt` using a custom markup format with hand-crafted delimiters:

```
^@^^#play#^^@^    +|>executable_keyword<|+    )-)play.py(-(
^@^^#add#^^@^     +|>mathematical<|+          )-)add.py(-(
```

Each line defines:
- **Command name** wrapped in `^@^^#...#^^@^`
- **Command type** wrapped in `+|>...<|+` (categories like `mathematical`, `executable_shortcut`, `pre-defined speech`)
- **Module file path** wrapped in `)-)...(-(`

This is essentially a hand-rolled structured data format — a bespoke alternative to JSON/CSV/XML, using visually distinctive delimiters that are unlikely to collide with normal text. A helper library (`Pvz_Functions.extract()`) parses these by delimiter.

### The Module System

Each command lives in its own `.py` file under `Modules/`. Every module follows the same contract:

```python
def RUN(arg):
    # parse arg, do work, print result
    ...

if len(sys.argv) > 1:
    RUN(sys.argv[1])
```

Modules are invoked as **subprocesses** — the main loop calls `subprocess.getoutput('python "module.py" "user input"')`. The entire user input string is passed as a single argument, and the module is responsible for parsing out its relevant portion.

This is a genuinely interesting design choice: each command is an isolated process. It can't crash the main loop, and it communicates results purely through stdout.

---

## The NLP Engine — How Natural Language Gets Parsed

This is the heart of CLINT and where the most creative engineering happens.

### Keyword Scanning

`Interactive_Mode()` keeps a dictionary of all registered command keywords. When input arrives, it scans for known keywords in the word list. When it finds one, it looks up the associated module file and runs it.

### Command Chaining

The most ambitious feature: CLINT supports **chaining multiple commands in a single sentence**. For example:

> "5 plus 3 minus 2 then say hello"

This is handled through two special string protocols:

- **`$-$`** — marks the beginning of inline-executable Python code returned by a module. When a module's output contains `$-$`, everything after it is executed directly via `exec()` in the main loop's context.
- **`%-%-%`** — marks the boundary between the current command's output and the **remaining unparsed input** that should be fed back into the loop.

The flow works like this:
1. User types: `"5 plus 3 then say hello"`
2. `plus.py` gets the full string, uses `segregate()` to split off its part (`5 plus 3`) from the rest (`say hello`)
3. `plus.py` outputs: `8.0 say hello`
4. The main loop sees there are still keywords in the output, so it loops again
5. `say.py` picks up `say hello`, speaks "hello"

The `segregate()` function in `Modular_Functions.py` is the key utility here — it takes the full input string, the list of all known keywords, and the current command's keyword, then splits the string at the boundary of the next keyword so each module only processes its own portion.

### The Akapi System (Alias Dictionary)

`aka_dictionary.txt` maps synonym groups so users can say things naturally:

```
introduce yourself, give intro,
mins, minutes, minute, min,
hrs, hours, hr, hour,
cls, clrscr, clear, clr,
```

Before processing, input is run through `P.akapi()` which normalizes aliases to their canonical form. So "clear the screen" and "clrscr" and "cls" all route to the same module.

There's even a dedicated interactive mode (`akapiMode`) for adding, modifying, and deleting aliases at runtime — the system was designed to be self-extending without touching code.

### The RAM System

`RAM.txt` contains response patterns for conversational inputs — greetings, acknowledgments, etc. Each line defines:
- A list of possible responses
- Trigger phrases
- Pattern matching rules

This gives CLINT some basic conversational ability beyond just executing commands.

---

## The Three Operating Modes

### 1. Interactive Mode (Default)
The natural language interface. Type human-readable sentences and CLINT figures out what to do. Supports command chaining, aliasing, text-to-speech responses, and math parsing.

### 2. Command Mode (`cmd_mode`)
An admin/developer mode for managing CLINT's command registry:
- **Define new modules** — register a keyword, type, and file path
- **Modify existing commands** — change what file a keyword points to
- **Delete commands** — remove from defined or undefined lists
- **Display** — view all registered and pending commands

Commands start as "undefined" (just a name and type) and become "defined" once linked to a module file. This two-stage approach means you could plan out future commands before implementing them.

### 3. Spexec Mode (Special Executable)
A raw multi-line Python code editor and executor built right into the assistant. You type Python code line by line, can modify lines by index, and then type "Execute" to run it all. It even tracks variables created during execution and cleans them up afterward to avoid polluting the main scope. Essentially a primitive REPL built inside CLINT.

---

## The Available Commands

| Command | Type | What It Does |
|---|---|---|
| `plus`, `add` | Mathematical | Addition with natural language ("5 plus 3", "add 5 and 3") |
| `minus`, `subtract` | Mathematical | Subtraction, understands "from" syntax |
| `multiply`, `into` | Mathematical | Multiplication |
| `divide`, `by` | Mathematical | Division |
| `play` | Executable | Fuzzy-searches a songs directory and plays the best match |
| `say` | Executable | Text-to-speech — speaks whatever follows |
| `intro` / `introduce yourself` | Pre-defined speech | CLINT introduces itself |
| `timer` | Executable | Countdown timer with voice announcements at half and quarter |
| `wait` | Executable | Pauses execution ("wait for 2 mins and 30 secs") — parses natural time units |
| `time` | Executable | Speaks and displays current time (12-hour format) |
| `date` | Executable | Speaks and displays current date |
| `today` | Executable | Speaks the full day ("A Wednesday of March 1 2026") |
| `now` | Executable | Speaks full date + time |
| `cls` / `clear` | Shortcut | Clears the screen |
| `playlist` / `songs` | Shortcut | Lists all files in the songs directory |
| `flushdns` | Shortcut | Flushes DNS cache |
| `hider` | Shortcut | Password-protected file hider utility |
| `exit` / `quit` | Shortcut | Exits CLINT |
| `vatican cameos` | Shortcut | Emergency shutdown — says "vatican cameos" and powers off the PC. A Sherlock Holmes reference. |

---

## Notable Design Patterns

### Subprocess Isolation
Each module runs as a separate Python process. The main loop is never at risk from a crashing module. This is a form of process-level sandboxing.

### String-as-Protocol
The `$-$` and `%-%-%` markers in module output form a mini protocol:
- `$-$` = "execute the following Python code in the caller's context"
- `%-%-%` = "everything after this is remaining input to process"

This allows modules to both return computed values AND inject executable behavior back into the main loop — a creative (if dangerous) form of inter-process communication.

### Self-Modifying Registry
CLINT can add, remove, and modify its own command definitions at runtime. The system was built to grow organically — new capabilities could be taught to it without restarting or editing source code.

### Custom Delimiters as Data Format
Rather than using JSON or CSV, the project uses visually distinctive delimiter pairs (`^@^^#...#^^@^`, `+|>...<|+`, `)-)...(-(`). These are ugly but functional — they're essentially impossible to accidentally type in normal text, making parsing reliable. It's a pragmatic solution.

### Logging Everything
The `readwriter()` function logs every input, mode change, and action to a master file with timestamps. This creates a full audit trail of every interaction.

---

## External Dependencies

- **`Pvz_Functions`** (aliased as `P`) — a custom helper library (not included in this repo) that provides utilities like `extract()` for parsing delimited files, `caps()` for case normalization, `akapi()` for alias resolution, `say()` for TTS, `colour()` for colored terminal output, date/time helpers, and more. This is the foundation library that CLINT builds on.
- **`pyttsx3`** — text-to-speech engine
- **`colorama` + `termcolor`** — colored terminal output
- The system was built for Windows (P: drive paths, `shutdown /s`, `cls` command, etc.)

---

## Summary

CLINT is a personal AI assistant with a modular, extensible architecture. At its core, it's a natural language command dispatcher — you speak to it in plain English, it identifies keywords, routes them to isolated module scripts, chains results together, and speaks back to you. It has a self-service command registry, an alias system for natural synonyms, conversational response patterns, and even a built-in Python code executor.

The ambition here is clear: build a JARVIS. The approach — keyword-based NLP, subprocess-isolated plugins, string-based IPC, self-modifying command registry — shows real systems thinking. The individual pieces (parsing, routing, chaining, aliasing, logging) all fit together into a coherent whole that's more than the sum of its parts.

---

## Origin Story & Philosophy

A 15-year-old, self-taught programmer watched Iron Man, wanted to build JARVIS, and googled "best language for AI." Python came up. The very first program was:

```python
inp = input(">>> ")
if(inp=="hey"):
    print("At your service Sire")
```

From there — armed with strings, if-else statements, loops, arrays, functions, and a healthy Stack Overflow dependency — the project that would become CLINT (originally called "DragOn") took shape. Classes were never learned. For loops were a late addition (an earlier version used only while loops). There was no knowledge of CSV, JSON, or databases — so the solution to "how do programs save things when shut down?" was arrived at independently: store everything in text files with custom delimiters. A reinvention born from necessity.

### The Core Idea

The philosophy is deceptively simple:

> **If I program and teach it one word a day, in a few years it will be intelligent enough.**

The system would split whatever you type into tokens, identify keywords that had been taught to it (`add`, `subtract`, `play`, `say`, ...), and perform individual operations on segments of the sentence until no keywords remain. Each cycle reduces the sentence further — computation as progressive rewriting.

**Example:** `"Add 5, 6 and 7 and subtract 11"`
1. Tokenize: `Add` 5 6 7 `and` `Subtract` 11
2. Process `Add`: → `18` `and` `Subtract` 11
3. Process `Subtract`: → `7`

This meant wrestling with the full ambiguity of English for every keyword. Take "subtract" — it has to handle:
- `Subtract [number] from [number]`
- `Subtract [number] and [number]`
- `[number] Subtract [number]` (doesn't arise in natural speech, but appears as intermediate output from chained operations like the example above)

Every word's behaviour in every possible sentence structure had to be manually accounted for. This is hand-crafted NLP in the most literal sense.

### What Killed It

A Windows update broke the implementation. The system was tightly coupled to Windows paths (P: drive), Windows commands (`shutdown /s`, `cls`), and specific local file structures. The surviving patches of code were archived to GitHub.

### Why It Matters Now

The duct-taped, keyword-matching approach could only scale so far — but the *vision* was always ahead of the tools. With the advent of powerful AI agents (Codex, Claude Code, etc.), the original dream of a personal AI assistant that understands natural language and executes commands is more achievable than ever. The question is no longer "can it be done" but "how do we architect it right this time."
