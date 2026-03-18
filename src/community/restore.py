"""
Restore command — re-import a previously forgotten token from .token_archive/.

Usage in REPL:
    restore <name>    — restore a specific archived token
    restore           — list all recoverable tokens
"""

import os
import shutil

from rich.console import Console

from src.community.importer import import_token
from src.config.settings import TOKEN_ARCHIVE_DIR

_MANIFEST = "manifest.cinnamonint.json"

console = Console()


def list_archived_tokens():
    """list all token packages in .token_archive/."""
    if not os.path.isdir(TOKEN_ARCHIVE_DIR):
        console.print("[dim]No archived tokens.[/]")
        return

    entries = sorted(
        e for e in os.listdir(TOKEN_ARCHIVE_DIR)
        if os.path.isdir(os.path.join(TOKEN_ARCHIVE_DIR, e))
        and os.path.exists(os.path.join(TOKEN_ARCHIVE_DIR, e, _MANIFEST))
    )

    if not entries:
        console.print("[dim]No archived tokens.[/]")
        return

    console.print("[bold]Archived tokens (recoverable):[/]")
    for name in entries:
        console.print(f"  [cyan]{name}[/]")
    console.print(f"\n[dim]Restore with: restore <name>[/]")


def restore_token(name, interactive=True):
    """restore a forgotten token from .token_archive/<name>/.

    parameters:
        name        — the token name (must match the archive directory name)
        interactive — if False, skip confirmation prompts (for testing)

    returns:
        True if the token was restored, False otherwise.
    """
    archive_path = os.path.join(TOKEN_ARCHIVE_DIR, name)

    if not os.path.isdir(archive_path):
        console.print(f"[red]No archived token named '[bold]{name}[/bold]'.[/]")
        list_archived_tokens()
        return False

    manifest = os.path.join(archive_path, _MANIFEST)
    if not os.path.exists(manifest):
        console.print(f"[red]Archive for '{name}' is missing its manifest.[/]")
        return False

    # import using existing import infrastructure
    result = import_token(archive_path, interactive=interactive)

    if not result:
        return False

    # remove from archive after successful restore
    shutil.rmtree(archive_path)
    console.print(f"[dim]Removed from archive.[/]")
    return True
