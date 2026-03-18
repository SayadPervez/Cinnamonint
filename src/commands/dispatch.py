"""
Command dispatcher — route REPL commands to their handlers.

Centralizes command detection and hardened-mode gating so main.py
stays clean (REPL loop + sentence processing only).
"""

import os

from rich.console import Console

from src.config.settings import detect_mode, MODE_HARDENED
from src.commands.logs import handle_logs_command
from src.community.exporter import export_token, export_tokens
from src.community.importer import import_token, import_tokens_from_dir
from src.community.forget import forget_token
from src.community.restore import restore_token, list_archived_tokens
from src.learn.learner import learn

console = Console()

# commands that modify the registry — blocked in hardened mode
_MUTATION_COMMANDS = ("learn", "forget", "restore", "import")


def dispatch(user_input):
    """try to handle user_input as a built-in command.

    returns:
        True  — command was handled (caller should skip sentence processing)
        False — not a command (caller should process as a sentence)
        None  — exit command (caller should quit the REPL)
    """
    stripped = user_input.strip()
    if not stripped:
        return True  # empty input — handled (do nothing)

    lower = stripped.lower()

    # --- exit ---
    if lower in ("exit", "quit", "q"):
        console.print("[dim]goodbye.[/]")
        return None

    # --- logs ---
    if lower.startswith("logs"):
        parts = stripped.split()
        handle_logs_command(parts)
        return True

    # --- mutation commands: single hardened-mode gate ---
    cmd_word = lower.split()[0]
    if cmd_word in _MUTATION_COMMANDS:
        if detect_mode() == MODE_HARDENED:
            console.print(
                f"[red]Cannot run '[bold]{cmd_word}[/bold]' in hardened mode.[/]"
            )
            return True
        return _dispatch_mutation(cmd_word, stripped)

    # --- export (read-only, allowed in both modes) ---
    if lower.startswith("export "):
        names = stripped.split()[1:]
        if len(names) == 1:
            export_token(names[0])
        else:
            export_tokens(names)
        return True

    # not a command
    return False


def _dispatch_mutation(cmd_word, stripped):
    """route a mutation command to its handler. assumes hardened check passed."""

    # --- learn ---
    if cmd_word == "learn":
        parts = stripped.split(None, 1)
        if len(parts) < 2:
            console.print("[red]Usage: learn <word>[/]")
            return True
        learn(parts[1].strip())
        return True

    # --- forget ---
    if cmd_word == "forget":
        parts = stripped.split(None, 1)
        if len(parts) < 2:
            console.print("[red]Usage: forget <token_name_or_alias>[/]")
            return True
        forget_token(parts[1].strip())
        return True

    # --- restore ---
    if cmd_word == "restore":
        parts = stripped.split(None, 1)
        if len(parts) == 1:
            list_archived_tokens()
        else:
            restore_token(parts[1].strip())
        return True

    # --- import ---
    if cmd_word == "import":
        parts = stripped.split(None, 1)
        if len(parts) < 2:
            console.print("[red]Usage: import <path>[/]")
            return True
        source = parts[1].strip()
        manifest_file = os.path.join(source, "manifest.cinnamonint.json")
        if os.path.exists(manifest_file):
            import_token(source)
        else:
            import_tokens_from_dir(source)
        return True

    return False
