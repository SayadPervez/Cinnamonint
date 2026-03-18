"""
Cinnamonint — entry point and REPL loop.
"""

import sys
import os
import readline

# ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console

from src.config.settings import detect_mode, MODE_HARDENED, HISTORY_FILE
from src.engine.processor import process
from src.cinnamonint_logging.logger import log_prompt
from src.cinnamonint_logging.iterations import log_iteration, prune_old_iterations
from src.commands.dispatch import dispatch
from src.learn.learner import check_pending_handover, handle_return_flow


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


def _on_limit_reached(iteration_count, current_sentence, warn=False):
    """called when an iteration limit is hit."""
    if warn:
        console.print(
            f"\n[red bold]{iteration_count} iterations reached. "
            f"This is unusual.[/]"
            f" Current state: [cyan]{current_sentence}[/]"
        )
    else:
        console.print(
            f"\n[yellow bold]{iteration_count} iterations reached.[/]"
            f" Current state: [cyan]{current_sentence}[/]"
        )
    answer = console.input("[yellow]Continue? [y/N]: [/]").strip().lower()
    return answer in ("y", "yes")


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

def _process_input(user_input):
    """process a single line of user input. returns True to continue, False to exit."""
    global _current_prompt_id, _iteration_records

    # --- try built-in commands first ---
    result = dispatch(user_input)
    if result is None:
        return False   # exit command
    if result is True:
        return True    # command handled

    # --- normal sentence processing ---
    stripped = user_input.strip()
    _iteration_records = []

    interactive = sys.stdin.isatty()
    final, iterations, status = process(
        stripped,
        on_iteration=_on_iteration,
        on_limit_reached=_on_limit_reached,
        interactive=interactive,
    )

    # log the prompt
    prompt_id = log_prompt(stripped, final, iterations, status)

    # log all buffered iterations
    for rec in _iteration_records:
        it_num, before, keyword, handler_path, after, duration = rec
        log_iteration(prompt_id, it_num, before, keyword, handler_path, after, duration)

    # prune old iteration data
    prune_old_iterations()

    # display result
    if final and final.strip():
        console.print(final)
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

    # --- check for pending learn handover ---
    pending_word = check_pending_handover()
    if pending_word:
        should_continue = handle_return_flow()
        if not should_continue:
            _save_history()
            return

    mode = detect_mode()
    mode_label = "workshop" if mode != MODE_HARDENED else "hardened"

    if os.environ.get("CINNAMONINT_TEST_DB") == "1":
        console.print("[yellow bold]⚠ Running against test registry (CINNAMONINT_TEST_DB=1)[/]")

    console.print(
        f"[bold green]cinnamonint[/] [dim]({mode_label} mode)[/]  —  "
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
