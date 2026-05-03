"""
REPL command handler for the user dictionary.

Commands:
    dictionary                    — list all ignored words and remembered corrections
    dictionary remove <w>         — remove a word from ignored list or corrections
"""

from rich.console import Console

from src.engine.user_dictionary import (
    list_words, remove_word,
    list_corrections, remove_correction,
)

console = Console()


def handle_dictionary_command(parts):
    """dispatch a dictionary command from the REPL."""
    if len(parts) == 1:
        _list_all()
        return

    sub = parts[1].lower()
    if sub == "remove" and len(parts) >= 3:
        word = parts[2].strip().lower()
        _remove(word)
    else:
        console.print(
            "[red]Usage: dictionary | dictionary remove <word>[/]"
        )


def _list_all():
    """list ignored words and remembered corrections."""
    words = list_words()
    corrections = list_corrections()

    if not words and not corrections:
        console.print("[dim]User dictionary is empty.[/]")
        return

    if words:
        console.print(f"[bold]Ignored words[/] ({len(words)}):")
        for w in words:
            console.print(f"  {w}")

    if corrections:
        console.print(f"[bold]Remembered corrections[/] ({len(corrections)}):")
        for typo, correction in corrections:
            console.print(f"  {typo} → {correction}")


def _remove(word):
    """remove a word from ignored list or corrections — checks both."""
    removed_word = remove_word(word)
    removed_correction = remove_correction(word)

    if removed_word and removed_correction:
        console.print(f"[green]Removed '{word}' from ignored words and corrections.[/]")
    elif removed_word:
        console.print(f"[green]Removed '{word}' from ignored words.[/]")
    elif removed_correction:
        console.print(f"[green]Removed correction for '{word}'.[/]")
    else:
        console.print(f"[yellow]'{word}' not found in ignored words or corrections.[/]")
