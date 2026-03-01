"""
Log commands — display prompts, traces, learning events, execution log.
"""

from rich.console import Console
from rich.table import Table

from src.aif_logging.logger import (
    get_recent_prompts,
    search_prompts,
    get_learning_events,
    get_recent_executions,
    get_executions_for_prompt,
)
from src.aif_logging.iterations import get_iterations

console = Console()


def handle_logs_command(parts):
    """process 'logs ...' commands."""
    if len(parts) < 2:
        _show_logs_help()
        return

    sub = parts[1]

    if sub == "recent":
        _show_recent_prompts()
    elif sub == "trace":
        if len(parts) < 3:
            console.print("[red]Usage: logs trace <prompt_id>[/]")
            return
        try:
            prompt_id = int(parts[2])
        except ValueError:
            console.print("[red]Prompt ID must be a number.[/]")
            return
        _show_trace(prompt_id)
    elif sub == "learned":
        _show_learning_events()
    elif sub == "search":
        if len(parts) < 3:
            console.print("[red]Usage: logs search <query>[/]")
            return
        query = " ".join(parts[2:])
        _show_search_results(query)
    elif sub == "exec":
        if len(parts) >= 3:
            try:
                prompt_id = int(parts[2])
                _show_exec_for_prompt(prompt_id)
            except ValueError:
                console.print("[red]Prompt ID must be a number.[/]")
        else:
            _show_recent_exec()
    else:
        _show_logs_help()


def _show_logs_help():
    console.print("[bold]Log commands:[/]")
    console.print("  logs recent           — last 20 prompts")
    console.print("  logs trace <id>       — iteration trace for prompt #id")
    console.print("  logs learned          — all learning events")
    console.print("  logs search <query>   — search prompts by text")
    console.print("  logs exec             — recent execution log")
    console.print("  logs exec <id>        — execution log for prompt #id")


def _show_recent_prompts():
    prompts = get_recent_prompts()
    if not prompts:
        console.print("[dim]No prompts logged yet.[/]")
        return
    table = Table(title="Recent Prompts")
    table.add_column("ID", style="dim")
    table.add_column("Input")
    table.add_column("Output")
    table.add_column("Iters", justify="right")
    table.add_column("Status")
    table.add_column("Time", style="dim")
    for p in prompts:
        table.add_row(
            str(p["id"]),
            _truncate(p["input_text"], 40),
            _truncate(p["final_output"] or "", 40),
            str(p["iteration_count"] or 0),
            p["status"],
            str(p["timestamp"]),
        )
    console.print(table)


def _show_trace(prompt_id):
    iters = get_iterations(prompt_id)
    if not iters:
        console.print(f"[dim]No iteration data for prompt #{prompt_id}.[/]")
        return
    table = Table(title=f"Iteration Trace — Prompt #{prompt_id}")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Before")
    table.add_column("Token", style="cyan")
    table.add_column("After")
    table.add_column("ms", justify="right", style="dim")
    for it in iters:
        table.add_row(
            str(it["iteration_num"]),
            _truncate(it["sentence_before"], 50),
            it["token_processed"] or "",
            _truncate(it["sentence_after"], 50),
            str(it["duration_ms"] or 0),
        )
    console.print(table)


def _show_learning_events():
    events = get_learning_events()
    if not events:
        console.print("[dim]No learning events yet.[/]")
        return
    table = Table(title="Learning Events")
    table.add_column("Token", style="cyan")
    table.add_column("Action")
    table.add_column("Source")
    table.add_column("Time", style="dim")
    for e in events:
        table.add_row(e["token_name"], e["action"], e["source"], str(e["timestamp"]))
    console.print(table)


def _show_search_results(query):
    results = search_prompts(query)
    if not results:
        console.print(f"[dim]No prompts matching '{query}'.[/]")
        return
    table = Table(title=f"Search: {query}")
    table.add_column("ID", style="dim")
    table.add_column("Input")
    table.add_column("Output")
    table.add_column("Time", style="dim")
    for p in results:
        table.add_row(
            str(p["id"]),
            _truncate(p["input_text"], 50),
            _truncate(p["final_output"] or "", 50),
            str(p["timestamp"]),
        )
    console.print(table)


def _show_recent_exec():
    entries = get_recent_executions()
    if not entries:
        console.print("[dim]No execution log entries yet.[/]")
        return
    table = Table(title="Recent Execution Log")
    table.add_column("ID", style="dim")
    table.add_column("Token", style="cyan")
    table.add_column("Action")
    table.add_column("Command/Path")
    table.add_column("Exit", justify="right")
    table.add_column("Time", style="dim")
    for e in entries:
        table.add_row(
            str(e["id"]),
            e["token_name"] or "",
            e["action_type"],
            _truncate(e["command"] or e["path"] or e["url"] or "", 40),
            str(e["exit_code"]) if e["exit_code"] is not None else "",
            str(e["timestamp"]),
        )
    console.print(table)


def _show_exec_for_prompt(prompt_id):
    entries = get_executions_for_prompt(prompt_id)
    if not entries:
        console.print(f"[dim]No execution log for prompt #{prompt_id}.[/]")
        return
    table = Table(title=f"Execution Log — Prompt #{prompt_id}")
    table.add_column("Token", style="cyan")
    table.add_column("Action")
    table.add_column("Command/Path")
    table.add_column("Exit", justify="right")
    table.add_column("Time", style="dim")
    for e in entries:
        table.add_row(
            e["token_name"] or "",
            e["action_type"],
            _truncate(e["command"] or e["path"] or e["url"] or "", 50),
            str(e["exit_code"]) if e["exit_code"] is not None else "",
            str(e["timestamp"]),
        )
    console.print(table)


def _truncate(s, length):
    """truncate a string with ellipsis if longer than length."""
    if len(s) <= length:
        return s
    return s[: length - 1] + "…"
