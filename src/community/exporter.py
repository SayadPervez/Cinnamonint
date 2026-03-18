"""
Token exporter — package registered tokens for sharing.

Package format:
    <token_name>/
        manifest.cinnamonint.json   — metadata
        handler.cinnamonint.py      — handler source code
        test.cinnamonint.py         — test file (if available)

Usage:
    export_token("plus")               # export by name
    export_token("+")                  # export by alias — resolves to "plus"
    export_tokens(["plus", "minus"])   # export multiple into one parent dir
"""

import json
import os
import shutil

from rich.console import Console

from src.registry.store import get_token, get_token_by_alias, get_aliases
from src.config.settings import EXPORTS_DIR, PROJECT_ROOT, TESTS_DIR

console = Console()


def export_tokens(names_or_aliases, output_dir=None):
    """export multiple tokens into a single parent directory.

    each token gets its own subfolder: <output_dir>/<token_name>/

    parameters:
        names_or_aliases — list of token names or aliases
        output_dir       — base directory (defaults to EXPORTS_DIR)

    returns:
        list of successfully created package directory paths.
    """
    if output_dir is None:
        output_dir = EXPORTS_DIR
    os.makedirs(output_dir, exist_ok=True)

    results = []
    for name in names_or_aliases:
        path = export_token(name, output_dir=output_dir)
        if path:
            results.append(path)

    if len(names_or_aliases) > 1:
        ok = len(results)
        total = len(names_or_aliases)
        console.print(
            f"\n[bold]Exported {ok}/{total} token(s) to "
            f"[bold]{output_dir}[/bold][/]"
        )

    return results


def export_token(name_or_alias, output_dir=None):
    """export a single token (by name or alias) as a shareable package.

    parameters:
        name_or_alias — canonical token name or any registered alias
        output_dir    — base directory for output (defaults to EXPORTS_DIR)

    returns:
        path to the created package directory, or None on failure.
    """
    # resolve alias → canonical token
    token = get_token(name_or_alias)
    if not token:
        token = get_token_by_alias(name_or_alias)
    if not token:
        console.print(
            f"[red]Token or alias '[bold]{name_or_alias}[/bold]' not found.[/]"
        )
        return None

    if output_dir is None:
        output_dir = EXPORTS_DIR

    token_name = token["name"]
    token_id = token["id"]
    aliases = get_aliases(token_id)

    # read handler source
    handler_path = os.path.join(PROJECT_ROOT, token["handler_path"])
    if not os.path.exists(handler_path):
        console.print(
            f"[red]Handler file not found: [bold]{token['handler_path']}[/bold][/]"
        )
        return None

    with open(handler_path, "r") as f:
        handler_source = f.read()

    # locate test file
    test_path = token.get("test_path")
    test_abs = os.path.join(PROJECT_ROOT, test_path) if test_path else None
    has_test = test_abs and os.path.exists(test_abs)

    # build manifest
    manifest = {
        "name": token_name,
        "aliases": aliases,
        "category": token["category"],
        "priority": token["priority"],
        "destructive": bool(token["destructive"]),
        "downloads": bool(token["downloads"]),
        "uploads": bool(token["uploads"]),
        "author": token.get("author", "local"),
        "version": token.get("version", "1.0.0"),
        "description": f"Token handler for '{token_name}'",
    }

    # create package directory
    package_dir = os.path.join(output_dir, token_name)
    os.makedirs(package_dir, exist_ok=True)

    # write manifest
    with open(os.path.join(package_dir, "manifest.cinnamonint.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # write handler
    with open(os.path.join(package_dir, "handler.cinnamonint.py"), "w") as f:
        f.write(handler_source)

    # copy test file
    if has_test:
        shutil.copy2(test_abs, os.path.join(package_dir, "test.cinnamonint.py"))

    resolved_note = (
        f" (resolved from alias '{name_or_alias}')"
        if name_or_alias != token_name
        else ""
    )
    console.print(
        f"[green]Exported '[bold]{token_name}[/bold]'{resolved_note} to "
        f"[bold]{package_dir}[/bold][/]"
    )
    console.print(
        f"  manifest.cinnamonint.json — {len(manifest['aliases'])} alias(es)"
    )
    console.print(
        f"  handler.cinnamonint.py    — {len(handler_source)} bytes"
    )
    console.print(
        f"  test.cinnamonint.py       — {'included' if has_test else 'none'}"
    )

    return package_dir
