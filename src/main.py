"""
AIF — entry point and REPL loop.
"""

import sys
import os
import readline

# ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console

from src.config.settings import detect_mode, MODE_HARDENED, HISTORY_FILE
from src.engine.processor import process
from src.aif_logging.logger import log_prompt
from src.aif_logging.iterations import log_iteration, prune_old_iterations
from src.commands.logs import handle_logs_command

console = Console()

# ---------------------------------------------------------------------------
# iteration callbacks
# ---------------------------------------------------------------------------

_current_prompt_id = None
_iteration_records = []


def _on_iteration(iteration_num, before, keyword, handler_path, after, duration_ms):
    """called after each reduction step — buffer for later logging."""
    _iteration_records.append(
        (iteration_num, before, keyword, handler_path, after, duration_ms)
    )


def _on_limit_reached(iteration_count, current_sentence):
    """called when the soft iteration limit is hit."""
    console.print(
        f"\n[yellow bold]{iteration_count} iterations reached.[/]"
        f" Current state: [cyan]{current_sentence}[/]"
    )
    answer = console.input("[yellow]Continue for 50 more? [y/N]: [/]").strip().lower()
    return answer in ("y", "yes")


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

def _process_input(user_input):
    """process a single line of user input. returns True to continue, False to exit."""
    global _current_prompt_id, _iteration_records

    stripped = user_input.strip()
    if not stripped:
        return True

    lower = stripped.lower()

    # --- exit commands ---
    if lower in ("exit", "quit", "q"):
        console.print("[dim]goodbye.[/]")
        return False

    # --- log commands ---
    if lower.startswith("logs"):
        parts = stripped.split()
        handle_logs_command(parts)
        return True

    # --- learn / unlearn placeholders (stage 3) ---
    mode = detect_mode()
    if lower.startswith("learn "):
        if mode == MODE_HARDENED:
            console.print("[red]Cannot learn in hardened mode.[/]")
        else:
            console.print("[yellow]Learn mode is not yet implemented (Stage 3).[/]")
        return True

    if lower.startswith("unlearn "):
        if mode == MODE_HARDENED:
            console.print("[red]Cannot unlearn in hardened mode.[/]")
        else:
            console.print("[yellow]Unlearn mode is not yet implemented (Stage 3).[/]")
        return True

    # --- normal sentence processing ---
    _iteration_records = []

    result, iterations, status = process(
        stripped,
        on_iteration=_on_iteration,
        on_limit_reached=_on_limit_reached,
    )

    # log the prompt
    prompt_id = log_prompt(stripped, result, iterations, status)

    # log all buffered iterations
    for rec in _iteration_records:
        it_num, before, keyword, handler_path, after, duration = rec
        log_iteration(prompt_id, it_num, before, keyword, handler_path, after, duration)

    # prune old iteration data
    prune_old_iterations()

    # display result
    if result and result.strip():
        console.print(result)
    elif iterations == 0:
        console.print(f"[dim]{stripped}[/]")

    return True


def _load_history():
    """load REPL history from file."""
    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass
    readline.set_history_length(1000)


def _save_history():
    """save REPL history to file."""
    try:
        readline.write_history_file(HISTORY_FILE)
    except OSError:
        pass


def repl():
    """main REPL loop."""
    _load_history()

    mode = detect_mode()
    mode_label = "workshop" if mode != MODE_HARDENED else "hardened"
    console.print(
        f"[bold green]aif[/] [dim]({mode_label} mode)[/]  —  "
        f"type a sentence, or [bold]exit[/] to quit"
    )

    while True:
        try:
            user_input = input("\033[1;32m>>> \033[0m")
            if not _process_input(user_input):
                break
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]goodbye.[/]")
            break

    _save_history()


def main():
    """entry point — handle piped input or start REPL."""
    if not sys.stdin.isatty():
        # piped input: process each line through the same gate as the REPL
        for line in sys.stdin:
            line = line.strip()
            if line:
                _process_input(line)
    else:
        repl()


if __name__ == "__main__":
    main()
