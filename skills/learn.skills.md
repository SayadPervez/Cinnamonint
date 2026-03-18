# Cinnamonint — Learn Skills

> Instructions for AI-assisted code generation of token handlers and tests.
> This file is the single source of truth for what a valid handler looks like.

---

## What is Cinnamonint?

Cinnamonint is an iterative sentence-reduction engine. User input is a sentence. Known tokens (keywords) are identified. The sentence is split at token boundaries, the token's handler processes its chunk, replaces itself with the result, and the engine loops until no tokens remain.

---

## Your Task

When asked to generate a handler and tests for a word:

1. Create the handler file: `tokens/<category>/<word>.py`
2. Create the test file: `tests/<category>/test_<word>.py`
3. Ensure `tests/<category>/` has an `__init__.py` (create if missing)
4. Ensure `tokens/<category>/` has an `__init__.py` (create if missing)

**That's it.** Do NOT touch `seed.py`, `registry.db`, or any other system files. The cinnamonint learn flow handles token registration automatically when the user returns to the REPL. Your job is only to create the handler and test files.

---

## Handler File Structure

Every handler `.py` file MUST follow this exact structure:

```python
"""
Token: <name>
Aliases: <comma-separated or "none">
Category: <category>
Priority: <int>
Destructive: <true/false>
"""

import re
# other stdlib imports as needed — NO EXTERNAL PACKAGES


METADATA = {
    "name": "<name>",
    "aliases": ["alias1", "alias2"],   # list of strings, can be empty []
    "category": "<category>",          # "math", "system", "utility", "media", etc.
    "priority": 2,                     # int — see priority rules below
    "destructive": False,              # True if modifies filesystem/network/system
    "downloads": False,                # True if performs any download
    "uploads": False,                  # True if performs any upload
}


def handle(sentence: str) -> str:
    """Process one occurrence of '<name>' in the sentence."""
    lower = sentence.lower()
    match = re.search(r'\b<keyword>\b', lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start]
    after = sentence[end:]

    # ... extract operands, compute result, build modified sentence ...

    return result
```

---

## Handler Contract — CRITICAL RULES

1. **Signature**: `def handle(sentence: str) -> str` — always.
2. **One occurrence per call**: Process exactly ONE occurrence of your keyword. The engine will call you again if more exist.
3. **Full sentence in, full sentence out**: You receive the entire current sentence. Return the entire modified sentence with your keyword and its operands replaced by the result.
4. **Case-insensitive matching**: Match your keyword case-insensitively (`re.search(r'\b<keyword>\b', lower)`) but preserve the case of non-keyword parts.
5. **No side effects in unflagged handlers**: Handlers where `destructive`, `downloads`, and `uploads` are all `False` must be pure functions — no file I/O, no network, no printing. They compute and return. Flagged handlers (any flag is `True`) MAY have side effects — network calls, filesystem operations, or printing to stdout — since that's explicitly what the flags signal.
6. **Stdlib only**: Use only Python standard library. NO external packages (no `requests`, no `numpy`, etc.).
7. **Graceful fallthrough**: If your keyword is not found, return the sentence unchanged.

---

## Token Boundary Awareness

When your handler consumes numbers or operands from the sentence, you MUST respect token boundaries. Do NOT consume operands that belong to another token.

**Use `find_token_boundary()` and `find_token_boundary_reverse()`** from `src.engine.tokenizer`:

```python
from src.engine.tokenizer import find_token_boundary, find_token_boundary_reverse

# To find where the next token starts (right boundary):
boundary = find_token_boundary(after_text, exclude_keywords={"your_keyword"})
right_region = after_text[:boundary]

# To find where the previous token ends (left boundary):
left_boundary = find_token_boundary_reverse(before_text, {"your_keyword"})
left_region = before_text[left_boundary:]
```

**Return value semantics:** Both functions return a **character offset** into the text argument.
- `find_token_boundary(text)` → position of the first character of the next known token. If no token found, returns `len(text)` (entire text is yours).
- `find_token_boundary_reverse(text)` → position just after the last known token. If no token found, returns `0` (entire text is yours).

```
# Example:
text = " example.com and say hello"
#        0123456789...
# If 'say' is a known token at position 17:
#   find_token_boundary(text, {"ping"}) → 17
#   text[:17] → " example.com and " (your operand region)
#   text[17:] → "say hello" (belongs to the next handler)
```

**Important:** These functions are imported lazily inside handler function bodies (not at module level). This is intentional — it avoids circular imports at module load time.

**When to use boundaries:**
- Handlers that consume ALL numbers on a side (add, multiply, divide) — MUST use boundaries
- Binary handlers that take exactly one number from each side (plus, minus, subtract) — use `find_token_boundary_reverse` for left side; right side naturally takes only the first number

---

## Priority Rules

| Priority | Token types | Reasoning |
|----------|-------------|-----------|
| 3 | multiply, divide, into, by | BODMAS — multiplication/division first |
| 2 | plus, minus, add, subtract | BODMAS — addition/subtraction second |
| 1 | say, speak, display, show | Actions — execute after computation |
| 0 | exit, quit, clear | Control — process last |

Choose the priority that fits your token's role. Same-priority tokens are processed left-to-right by position in the sentence.

---

## METADATA Constant — REQUIRED

The `METADATA` dict is how the system registers your token. It MUST be a module-level constant named exactly `METADATA`.

**Required keys:**
- `name` (str): the primary keyword — lowercase, no spaces for single-word tokens
- `aliases` (list[str]): alternative keywords that trigger this handler. Can be `[]`
- `category` (str): one of `"math"`, `"system"`, `"utility"`, `"media"`, or a new category
- `priority` (int): processing precedence (see priority rules above)
- `destructive` (bool): `True` if this handler modifies filesystems, runs shell commands, or alters system state
- `downloads` (bool): `True` if this handler downloads anything from the network
- `uploads` (bool): `True` if this handler uploads anything to the network

---

## `extract_operands` — REQUIRED for Destructive/Download/Upload Tokens

If `destructive`, `downloads`, or `uploads` is `True`, you MUST also implement:

```python
def extract_operands(sentence: str) -> tuple:
    """Extract operands for approval hashing.

    Returns a 3-tuple: (canonical_token_name, parameters, context)
    - canonical_token_name: str — the token name (e.g., "flushdns")
    - parameters: str — the key arguments (e.g., "./file.txt")
    - context: str — additional context (e.g., "recursive")

    This tuple is hashed for the approval system. Same operation in different
    sentences should produce the same tuple so approval only prompts once.
    """
    # Example for a "delete" token:
    match = re.search(r'\bdelete\b\s+(.+)', sentence.lower())
    if match:
        target = match.group(1).strip()
        return ("delete", target, "")
    return ("delete", "", "")
```

**Why?** The approval system hashes this tuple. If the same operation appears in different sentences (e.g., "delete foo.txt" vs "please delete foo.txt and exit"), both produce the same hash and only prompt once.

Non-flagged handlers (math, say, etc.) do NOT need this function.

---

## Multi-Result Handlers (Print + Return Pattern)

Some handlers process multiple items and need to display results to the user (e.g., pinging multiple URLs, listing files). These follow a dual pattern:

- **Single item:** Replace the keyword and operand inline with the result (composable in sentence chains).
  - `"say ping example.com"` → handler returns `"say reachable"` → `say` processes next
- **Multiple items:** Print the results to stdout (table, list, etc.) and remove the keyword section from the sentence, returning only the remaining text.
  - `"ping a.com, b.com and say 1"` → prints the result table, returns `"and say 1"`

This keeps single-item usage composable in sentence chains while giving multi-item usage readable output.

**Implementation pattern:**
```python
def handle(sentence: str) -> str:
    # ... find keyword, extract operands ...

    if len(items) == 1:
        # single item — inline result for composability
        result_str = process_single(items[0])
        return f"{before}{result_str}{remaining}".strip()
    else:
        # multiple items — print results, remove self from sentence
        results = [process_single(item) for item in items]
        for item, result in zip(items, results):
            print(f"{item} -> {result}")
        return remaining.strip()
```

---

## Test File Structure

Every test file MUST follow this structure:

```python
"""
Test suite for the '<name>' token handler.
"""

import unittest
from tokens.<category>.<name> import handle


class test_<name>(unittest.TestCase):

    def test_basic(self):
        """Most common use case."""
        self.assertEqual(handle("<basic input>"), "<expected output>")

    def test_no_keyword(self):
        """Sentence without the keyword — should return unchanged."""
        self.assertEqual(handle("hello world"), "hello world")

    def test_with_other_tokens(self):
        """Keyword mixed with other token keywords — boundary respect."""
        self.assertEqual(handle("<input with other tokens>"), "<expected>")

    # ... more test cases covering:
    # - edge cases (empty operands, no numbers, etc.)
    # - all supported phrase patterns
    # - negative numbers / decimals where applicable
    # - left-to-right processing (only first occurrence handled)


if __name__ == "__main__":
    unittest.main()
```

**Test requirements:**
- Minimum 5 test cases per handler
- MUST include `test_no_keyword` — verifies graceful fallthrough
- MUST include a chaining test — keyword mixed with another token
- Class name: `test_<name>` (snake_case, NOT PascalCase)
- Import path: `from tokens.<category>.<name> import handle`
- Use `unittest.TestCase` (not raw assert)
- Tests call `handle()` directly against the real engine/DB — do NOT mock `find_token_boundary` or other internals unless you have a specific reason (the seeded DB has all tokens registered, so boundary detection works in tests)
- If you need to mock something (e.g., `os.system` in a handler that calls it), patch it at the source: `@patch("os.system")`, not on your handler module

---

## Running Tests During Development

Your new token is NOT in the production registry yet — the learn flow handles that when the user returns to cinnamonint. To test with full boundary detection and engine routing, use the test setup tool:

```bash
# 1. Register your token in a test copy of the registry
python -m src.learn.test_setup <word>

# 2. Run the full test suite against the test registry
CINNAMONINT_TEST_DB=1 python -m pytest tests/

# 3. Or run just your test file
CINNAMONINT_TEST_DB=1 python -m pytest tests/<category>/test_<word>.py

# 4. Clean up when done
python -m src.learn.test_setup --clean
```

**What `test_setup` does:**
1. Copies `db/registry.db` → `db/test_registry.db`
2. Parses `METADATA` from your handler file
3. Registers the new token in `test_registry.db`

The `CINNAMONINT_TEST_DB=1` env var makes all code read from the test registry instead of production. The `.learn_handover.json` handover gate is also skipped in test mode.

**Important:**
- Do NOT manually edit `seed.py` or `registry.db`
- Do NOT delete `.learn_handover.json` — it tracks the active learn session
- When the user returns to cinnamonint, the return flow will register your token in the production DB and run tests again for final validation

---

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Handler file | `tokens/<category>/<name>.py` | `tokens/math/plus.py` |
| Test file | `tests/<category>/test_<name>.py` | `tests/math/test_plus.py` |
| Function | `snake_case` | `handle()`, `extract_operands()` |
| Class | `snake_case` | `test_plus` |
| Constants | `UPPER_SNAKE_CASE` | `METADATA` |
| Variables | `snake_case` | `left_val`, `result_str` |

**NO PascalCase or camelCase anywhere.**

---

## Number Formatting

When a handler produces a numeric result, format it properly:

```python
def _format_number(n):
    """Integer if whole, float otherwise."""
    if n == int(n):
        return str(int(n))
    return str(n)
```

This ensures `4.0` becomes `"4"` and `3.14` stays `"3.14"`.

---

## Example: Complete Handler + Test

### `tokens/math/plus.py`

```python
"""
Token: plus
Aliases: +
Category: math
Priority: 2
Destructive: false
"""

import re


METADATA = {
    "name": "plus",
    "aliases": ["+"],
    "category": "math",
    "priority": 2,
    "destructive": False,
    "downloads": False,
    "uploads": False,
}


def handle(sentence: str) -> str:
    """Process one occurrence of 'plus' in the sentence."""
    lower = sentence.lower()
    match = re.search(r'\bplus\b', lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start]
    after = sentence[end:]

    from src.engine.tokenizer import find_token_boundary_reverse
    left_boundary = find_token_boundary_reverse(before, {"plus", "+"})
    left_region = before[left_boundary:]

    left_numbers = re.findall(r'[-+]?\d*\.?\d+', left_region)
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        result = left_val + right_val
        remaining_before = before[:left_boundary] + _remove_last_number(left_region)
        remaining_after = right_match.group(2)
        result_str = _format_number(result)
        return f"{remaining_before}{result_str}{remaining_after}".strip()

    return sentence


def _remove_last_number(s):
    matches = list(re.finditer(r'[-+]?\d*\.?\d+', s))
    if not matches:
        return s
    return s[:matches[-1].start()]


def _format_number(n):
    if n == int(n):
        return str(int(n))
    return str(n)
```

### `tests/math/test_plus.py`

```python
"""
Test suite for the 'plus' token handler.
"""

import unittest
from tokens.math.plus import handle


class test_plus(unittest.TestCase):

    def test_basic_addition(self):
        self.assertEqual(handle("5 plus 3"), "8")

    def test_larger_numbers(self):
        self.assertEqual(handle("10 plus 20"), "30")

    def test_decimal_addition(self):
        self.assertEqual(handle("1.5 plus 2.5"), "4")

    def test_chained_with_other_token(self):
        self.assertEqual(handle("5 plus 3 minus 1"), "8 minus 1")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_negative_result(self):
        self.assertEqual(handle("-5 plus 3"), "-2")

    def test_zero(self):
        self.assertEqual(handle("0 plus 0"), "0")

    def test_only_takes_last_left_number(self):
        self.assertEqual(handle("10 hello 5 plus 3"), "10 hello 8")


if __name__ == "__main__":
    unittest.main()
```

---

## DO's

- Use `re.search(r'\b<keyword>\b', lower)` for keyword matching
- Process exactly one occurrence per call
- Respect token boundaries via `find_token_boundary` / `find_token_boundary_reverse`
- Return the full modified sentence
- Keep handlers self-contained — each handler IS its own parser
- Use stdlib only
- Test at least 5 cases including no-keyword and chaining
- Include `METADATA` as a module-level dict constant
- Use `.strip()` on the final return value to avoid leading/trailing whitespace
- When assembling `f"{remaining_before}{result_str}{remaining_after}"`, the natural whitespace from sentence slicing is preserved — `.strip()` at the end handles edge cases

## DON'Ts

- Do NOT use PascalCase or camelCase anywhere
- Do NOT import external packages
- Do NOT process more than one occurrence of your keyword per call
- Do NOT consume operands past a token boundary
- Do NOT use `exec()`, `eval()`, or `__import__()`
- Do NOT print to stdout in unflagged handlers — return the result as a string (flagged handlers may print)
- Do NOT modify global state
- Do NOT add the `METADATA` dict to the `__init__.py` files
- Do NOT use `assert` in tests — use `self.assertEqual` etc.
- Do NOT name test classes with PascalCase — use `test_<name>`
- Do NOT edit `seed.py` or manually modify `registry.db` — the learn flow handles registration
- Do NOT delete `.learn_handover.json` — it tracks the active learn session
- Do NOT mock `find_token_boundary` unless absolutely necessary — tests run against the real registry
