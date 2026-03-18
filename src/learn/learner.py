"""
Learn mode orchestrator — handles the full learn lifecycle.

Handover flow:
  1. Pre-checks (dirty tree, pending handover, token exists)
  2. Copy prompt to clipboard, print message
  3. Git commit "learn: <word>. handover initiated"
  4. Write .learn_handover.json with commit hash
  5. Wait 3s, open VS Code, exit REPL

Return flow (on next startup):
  1. Detect .learn_handover.json
  2. Ask user if they're ready to test
  3. Verify files exist + parse METADATA
  4. Run pytest
  5. On pass: commit, register, clear handover
  6. On fail: offer IDE reopen or revert
"""

import json
import os
import ast
import time
import subprocess
import shutil
import sys

from rich.console import Console

from src.config.settings import (
    PROJECT_ROOT, LEARN_HANDOVER_FILE, EDITOR_COMMAND,
    TOKENS_DIR, TESTS_DIR,
)
from src.registry.store import get_token, add_token
from src.learn.tester import run_full_test_suite
from src.safety.sandbox import auto_detect_flags, display_code_with_findings, analyze_handler_code, has_extract_operands

console = Console()


# ---------------------------------------------------------------------------
# handover initiation (called from dispatch)
# ---------------------------------------------------------------------------

def learn(word):
    """initiate learn mode for a new token. may exit the process."""
    word = word.strip().lower()

    if not _pre_checks(word):
        return

    prompt = _build_prompt(word)
    _copy_to_clipboard(prompt)

    console.print(
        "\n[bold green]Prompt template generated and copied to clipboard.[/]\n"
        "Opening your fav IDE. Paste the prompt to your agent "
        "and come back to continue.\n"
    )

    commit_hash = _git_commit_handover(word)
    if not commit_hash:
        return

    _write_handover_file(word, commit_hash)

    time.sleep(3)
    _open_editor()
    _exit_repl()


# ---------------------------------------------------------------------------
# return flow (called from main.py on startup)
# ---------------------------------------------------------------------------

def check_pending_handover():
    """check if a learn handover is pending. returns the word or None.

    returns None in test mode (CINNAMONINT_TEST_DB=1) — the handover
    gate only applies to the production REPL, not the test environment.
    """
    if os.environ.get("CINNAMONINT_TEST_DB") == "1":
        return None
    if not os.path.exists(LEARN_HANDOVER_FILE):
        return None
    try:
        with open(LEARN_HANDOVER_FILE, "r") as f:
            data = json.load(f)
        return data.get("word")
    except (json.JSONDecodeError, OSError):
        return None


def handle_return_flow():
    """handle the return from IDE handover. returns True to enter REPL, False to exit."""
    data = _read_handover_file()
    if not data:
        _clear_handover()
        return True

    word = data["word"]
    commit_hash = data["commit_hash"]

    console.print(
        f"\n[bold cyan]Hope you have created and implemented [green]{word}[/green].[/]"
    )
    answer = console.input("Shall we continue with testing your addition? [bold][y/n][/]: ").strip().lower()

    if answer in ("y", "yes"):
        return _flow_yes(word, commit_hash)
    else:
        return _flow_no(word, commit_hash)


# ---------------------------------------------------------------------------
# YES branch
# ---------------------------------------------------------------------------

def _flow_yes(word, commit_hash):
    """user says yes — verify files, run tests, register or handle failure."""

    # verify handler file exists and find category from METADATA
    handler_path, metadata = _find_and_validate_handler(word)
    if handler_path is None:
        return _ask_reopen_or_revert(word, commit_hash)

    # verify test file exists
    category = metadata["category"]
    test_rel = os.path.join("tests", category, f"test_{word}.py")
    test_abs = os.path.join(PROJECT_ROOT, test_rel)
    if not os.path.exists(test_abs):
        console.print(f"[red]Missing test file:[/] {test_rel}")
        return _ask_reopen_or_revert(word, commit_hash)

    # static analysis — show findings, auto-flag
    handler_abs = os.path.join(PROJECT_ROOT, handler_path)
    with open(handler_abs, "r") as f:
        source = f.read()
    findings = analyze_handler_code(source)
    if findings:
        console.print("\n[yellow bold]Static analysis findings:[/]")
        display_code_with_findings(source, findings)

    detected_flags = auto_detect_flags(source)
    _warn_flag_mismatch(metadata, detected_flags)

    # check extract_operands for flagged tokens
    is_flagged = metadata["destructive"] or metadata["downloads"] or metadata["uploads"]
    if is_flagged and not has_extract_operands(source):
        console.print(
            "[yellow bold]Warning:[/] This token is flagged "
            "(destructive/downloads/uploads) but does not implement "
            "[cyan]extract_operands()[/]. The approval system will "
            "fall back to full-sentence hashing."
        )

    # run tests
    console.print("\n[bold]Running test suite...[/]\n")
    passed, output = run_full_test_suite()

    if passed:
        console.print("[bold green]All tests passed![/]\n")
        _commit_success(word)
        _register_token(word, metadata, handler_path, test_rel)
        _clear_handover()
        console.print(f"[bold green]Token '{word}' learned and registered successfully![/]\n")
        return True
    else:
        console.print("[bold red]Tests failed.[/]\n")
        console.print(output)
        console.print("\n[red]Cannot have a token that fails tests.[/]")
        return _ask_reopen_or_revert(word, commit_hash)


# ---------------------------------------------------------------------------
# NO branch
# ---------------------------------------------------------------------------

def _flow_no(word, commit_hash):
    """user says no — ask if they want to revert."""
    answer = console.input(
        "Do you wish to revert to the state before learn? [bold][y/n][/]: "
    ).strip().lower()

    if answer in ("y", "yes"):
        if _revert_to_before_learn(commit_hash, word):
            _clear_handover()
        else:
            _clear_handover()
        return True
    else:
        _clear_handover()
        console.print("[dim]Keeping current state as-is.[/]\n")
        return True


# ---------------------------------------------------------------------------
# reopen-or-revert fork (shared by YES-fail paths)
# ---------------------------------------------------------------------------

def _ask_reopen_or_revert(word, commit_hash):
    """ask user to reopen IDE or revert."""
    answer = console.input(
        "Would you like to open the IDE to fix? [bold][y/n][/]: "
    ).strip().lower()

    if answer in ("y", "yes"):
        _open_editor()
        # handover persists — do NOT clear
        console.print("[dim]Handover persists. Fix and reopen cinnamonint.[/]")
        return False  # signal to exit REPL
    else:
        _revert_to_before_learn(commit_hash, word)
        _clear_handover()
        return True


# ---------------------------------------------------------------------------
# pre-checks
# ---------------------------------------------------------------------------

def _pre_checks(word):
    """run all pre-handover guards. returns True if all clear."""
    # pending handover?
    if os.path.exists(LEARN_HANDOVER_FILE):
        data = _read_handover_file()
        prev_word = data.get("word", "unknown") if data else "unknown"
        console.print(
            f"[red]You have a pending learn session for "
            f"'[bold]{prev_word}[/bold]'. Complete it first.[/]"
        )
        return False

    # token already exists?
    existing = get_token(word)
    if existing:
        console.print(f"[red]'{word}' is already a registered token.[/]")
        return False

    # dirty working tree?
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    if result.stdout.strip():
        console.print(
            "[red]You have uncommitted changes. "
            "Commit or stash before learning.[/]"
        )
        return False

    return True


# ---------------------------------------------------------------------------
# prompt + clipboard
# ---------------------------------------------------------------------------

def _build_prompt(word):
    """construct the prompt string for the user's AI tool."""
    return (
        f"refer the skills/learn.skills.md file to understand what and what not "
        f"is required. generate handler and tests for {word}. "
        f"refer skills/learn_flow.skills.md for the learn flow (handover, "
        f"testing, registration, revert)."
    )


def _copy_to_clipboard(text):
    """copy text to system clipboard. prints fallback if tools unavailable."""
    clipboard_commands = [
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["wl-copy"],
        ["pbcopy"],  # macOS
    ]

    for cmd in clipboard_commands:
        if shutil.which(cmd[0]):
            try:
                proc = subprocess.Popen(
                    cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                proc.communicate(input=text.encode())
                if proc.returncode == 0:
                    return
            except OSError:
                continue

    # fallback — print to terminal
    console.print(
        "\n[yellow]Could not copy to clipboard. Here's the prompt — "
        "copy it manually:[/]\n"
    )
    console.print(f"[cyan]{text}[/]\n")


# ---------------------------------------------------------------------------
# git operations
# ---------------------------------------------------------------------------

def _git_commit_handover(word):
    """stage all and commit. returns the commit hash or None on failure."""
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=PROJECT_ROOT, check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"learn: {word}. handover initiated",
             "--allow-empty"],
            cwd=PROJECT_ROOT, check=True,
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git error during handover commit: {e}[/]")
        return None


def _commit_success(word):
    """commit the learned token files."""
    try:
        subprocess.run(
            ["git", "add", "tokens/", "tests/", "src/"],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"learn: {word} successful",
             "--allow-empty"],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Git commit warning: {e}[/]")


def _verify_commit_exists(commit_hash):
    """check if a commit hash exists in the repo."""
    result = subprocess.run(
        ["git", "cat-file", "-t", commit_hash],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "commit"


def _revert_to_before_learn(commit_hash, word):
    """hard reset to the handover commit, then soft reset HEAD~1.

    returns True on success, False on failure.
    """
    if not _verify_commit_exists(commit_hash):
        console.print(
            f"[red bold]Cannot revert — handover commit [cyan]{commit_hash[:8]}[/cyan] "
            f"not found in git history. Manual cleanup required.[/]"
        )
        return False

    try:
        subprocess.run(
            ["git", "reset", "--hard", commit_hash],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "reset", "--soft", "HEAD~1"],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )
        console.print(f"[green]Reverted to state before learning '{word}'.[/]\n")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git revert failed: {e}[/]")
        return False


# ---------------------------------------------------------------------------
# handover file management
# ---------------------------------------------------------------------------

def _write_handover_file(word, commit_hash):
    """write .learn_handover.json with the current state."""
    data = {
        "word": word,
        "commit_hash": commit_hash,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(LEARN_HANDOVER_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _read_handover_file():
    """read and return .learn_handover.json contents, or None."""
    try:
        with open(LEARN_HANDOVER_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return None


def _clear_handover():
    """delete the handover state file."""
    try:
        os.remove(LEARN_HANDOVER_FILE)
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# editor
# ---------------------------------------------------------------------------

def _open_editor():
    """open the configured editor on the project root."""
    cmd = EDITOR_COMMAND.split()
    cmd.append(PROJECT_ROOT)
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        console.print(f"[yellow]Could not open editor ({EDITOR_COMMAND}): {e}[/]")


def _exit_repl():
    """exit the process cleanly."""
    sys.exit(0)


# ---------------------------------------------------------------------------
# file validation + METADATA parsing
# ---------------------------------------------------------------------------

def _find_and_validate_handler(word):
    """find the handler file and parse its METADATA.

    searches tokens/<any_category>/<word>.py for the handler.

    returns (handler_rel_path, metadata_dict) or (None, None) on failure.
    """
    # scan token directories for the handler file
    handler_filename = f"{word}.py"
    handler_path = None

    for category_dir in os.listdir(TOKENS_DIR):
        cat_path = os.path.join(TOKENS_DIR, category_dir)
        if not os.path.isdir(cat_path):
            continue
        candidate = os.path.join(cat_path, handler_filename)
        if os.path.exists(candidate):
            handler_path = os.path.join("tokens", category_dir, handler_filename)
            break

    if handler_path is None:
        console.print(
            f"[red]Handler file not found:[/] tokens/<category>/{word}.py\n"
            f"[dim]Looked in: {TOKENS_DIR}[/]"
        )
        return None, None

    # parse METADATA from the file
    abs_path = os.path.join(PROJECT_ROOT, handler_path)
    metadata = _parse_metadata(abs_path)
    if metadata is None:
        return None, None

    return handler_path, metadata


def _parse_metadata(filepath):
    """extract the METADATA dict constant from a handler file.

    returns the dict or None on failure.
    """
    try:
        with open(filepath, "r") as f:
            source = f.read()
        tree = ast.parse(source)
    except (OSError, SyntaxError) as e:
        console.print(f"[red]Cannot parse handler file: {e}[/]")
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "METADATA":
                    try:
                        value = ast.literal_eval(node.value)
                        if isinstance(value, dict):
                            if _validate_metadata(value):
                                return value
                    except (ValueError, TypeError):
                        pass

    console.print(
        "[red]METADATA constant not found or malformed in handler file.[/]\n"
        "[dim]Must be a module-level dict with keys: "
        "name, aliases, category, priority, destructive, downloads, uploads[/]"
    )
    return None


def _validate_metadata(meta):
    """check that all required keys are present and correct type."""
    required = {
        "name": str,
        "aliases": list,
        "category": str,
        "priority": int,
        "destructive": bool,
        "downloads": bool,
        "uploads": bool,
    }
    for key, expected_type in required.items():
        if key not in meta:
            console.print(f"[red]METADATA missing required key: '{key}'[/]")
            return False
        if not isinstance(meta[key], expected_type):
            console.print(
                f"[red]METADATA['{key}'] must be {expected_type.__name__}, "
                f"got {type(meta[key]).__name__}[/]"
            )
            return False
    return True


# ---------------------------------------------------------------------------
# token registration
# ---------------------------------------------------------------------------

def _register_token(word, metadata, handler_path, test_path):
    """register the new token in the database."""
    add_token(
        name=metadata["name"],
        category=metadata["category"],
        priority=metadata["priority"],
        handler_path=handler_path,
        aliases=metadata["aliases"] if metadata["aliases"] else None,
        destructive=metadata["destructive"],
        downloads=metadata["downloads"],
        uploads=metadata["uploads"],
        author="local",
        source="learn",
        version="1.0.0",
        test_path=test_path,
    )


# ---------------------------------------------------------------------------
# flag mismatch warning
# ---------------------------------------------------------------------------

def _warn_flag_mismatch(metadata, detected_flags):
    """warn if METADATA flags disagree with static analysis detection."""
    for flag in ("destructive", "downloads", "uploads"):
        if detected_flags.get(flag) and not metadata.get(flag):
            console.print(
                f"[yellow bold]Warning:[/] Static analysis detected "
                f"[red]{flag}[/] patterns but METADATA has "
                f"`{flag}: False`. Consider updating METADATA."
            )
