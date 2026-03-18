"""
Forget command — remove a registered token, its handler file, and test file.

Archives the full package (manifest + handler + test) to .token_archive/
so recovery is just: restore <name>

Seeded (source='seed') tokens cannot be forgotten — user must re-seed manually.

Usage in REPL:
    forget <token_name_or_alias>
    forget ping
    forget +         (resolves alias → forgets 'plus')
"""

import json
import os

from rich.console import Console

from src.registry.store import (
    get_token,
    get_token_by_alias,
    get_aliases,
    remove_token,
    remove_approvals_for_token,
)
from src.cinnamonint_logging.logger import log_learning_event
from src.community.exporter import export_token
from src.config.settings import PROJECT_ROOT, TOKEN_ARCHIVE_DIR

console = Console()


def forget_token(name_or_alias, interactive=True):
    """remove a token from the registry, archive it as a full package first.

    seeded tokens (source='seed') are protected and cannot be forgotten.

    parameters:
        name_or_alias — canonical token name or any registered alias
        interactive   — if False, skip confirmation prompt (for testing)

    returns:
        True if the token was forgotten, False otherwise.
    """
    # resolve alias → canonical token
    token = get_token(name_or_alias)
    if not token:
        token = get_token_by_alias(name_or_alias)
    if not token:
        console.print(
            f"[red]Token or alias '[bold]{name_or_alias}[/bold]' not found.[/]"
        )
        return False

    token_name = token["name"]
    token_id = token["id"]
    category = token["category"]
    aliases = get_aliases(token_id)

    # block seeded tokens
    if token.get("source") == "seed":
        console.print(
            f"[red]Cannot forget seeded token '[bold]{token_name}[/bold]'.[/]\n"
            f"[dim]Seeded tokens are part of the core installation. "
            f"To remove them, delete the DB and re-seed manually.[/]"
        )
        return False

    # display what will be removed
    console.print(f"\n[bold]Forget '[bold]{token_name}[/bold]'[/]")
    console.print(f"  Category:  {category}")
    console.print(f"  Aliases:   {', '.join(aliases) if aliases else '(none)'}")
    console.print(f"  Handler:   {token['handler_path']}")

    test_path = token.get("test_path")
    test_abs = os.path.join(PROJECT_ROOT, test_path) if test_path else None
    has_test = test_abs and os.path.exists(test_abs)
    if has_test:
        console.print(f"  Test file: {test_path}")

    # confirm with user
    if interactive:
        answer = console.input(
            f"\n[yellow]This will remove '{token_name}' and all its aliases. "
            f"Continue? [y/N]: [/]"
        ).strip().lower()
        if answer not in ("y", "yes"):
            console.print("[dim]Cancelled.[/]")
            return False

    # archive as full package (manifest + handler + test) for recovery
    archive_path = export_token(token_name, output_dir=TOKEN_ARCHIVE_DIR)
    if archive_path:
        rel = os.path.relpath(archive_path, PROJECT_ROOT)
        console.print(f"[dim]Archived to {rel}/ — recover with: restore {token_name}[/]")

    # delete handler file
    handler_abs = os.path.join(PROJECT_ROOT, token["handler_path"])
    if os.path.exists(handler_abs):
        os.remove(handler_abs)

    # delete test file
    if has_test:
        os.remove(test_abs)

    # remove approvals
    remove_approvals_for_token(token_id)

    # remove from DB (cascades to aliases)
    remove_token(token_name)

    # log the event
    log_learning_event(
        token_name, "forget",
        details=json.dumps({
            "category": category,
            "aliases": aliases,
            "handler_path": token["handler_path"],
        }),
    )

    console.print(f"[green]Token '[bold]{token_name}[/bold]' forgotten.[/]")
    return True
