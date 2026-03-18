"""
Token importer — import a token package from a local directory.

Package format (recognised by manifest.cinnamonint.json in the directory):
    <token_name>/
        manifest.cinnamonint.json   — metadata
        handler.cinnamonint.py      — handler source code
        test.cinnamonint.py         — test file (optional)

Single import:
    import_token("/path/to/plus/")

Bulk import (scans immediate subfolders for cinnamonint packages):
    import_tokens_from_dir("/path/to/my-tokens/")
"""

import json
import os
import shutil
import subprocess
import sys

from rich.console import Console
from rich.syntax import Syntax

from src.registry.store import (
    add_token,
    remove_token,
    get_token,
    get_token_by_alias,
    token_exists,
)
from src.safety.sandbox import (
    analyze_handler_code,
    display_code_with_findings,
    auto_detect_flags,
    has_extract_operands,
)
from src.cinnamonint_logging.logger import log_learning_event
from src.config.settings import PROJECT_ROOT, TOKENS_DIR, TESTS_DIR

console = Console()

# filename constants
_MANIFEST = "manifest.cinnamonint.json"
_HANDLER  = "handler.cinnamonint.py"
_TEST     = "test.cinnamonint.py"


def import_tokens_from_dir(parent_dir, interactive=True):
    """scan immediate subfolders of parent_dir for cinnamonint packages and import each.

    a subfolder is a cinnamonint package if it contains manifest.cinnamonint.json.

    parameters:
        parent_dir  — path to the directory containing token subfolders
        interactive — if False, skip approval prompts (for testing)

    returns:
        list of (token_name, success) tuples.
    """
    parent_dir = os.path.abspath(parent_dir)
    if not os.path.isdir(parent_dir):
        console.print(f"[red]Directory not found: [bold]{parent_dir}[/bold][/]")
        return []

    found = [
        os.path.join(parent_dir, entry)
        for entry in sorted(os.listdir(parent_dir))
        if os.path.isdir(os.path.join(parent_dir, entry))
        and os.path.exists(os.path.join(parent_dir, entry, _MANIFEST))
    ]

    if not found:
        console.print(
            f"[yellow]No cinnamonint packages found in [bold]{parent_dir}[/bold].[/]\n"
            f"[dim](looking for subdirectories containing {_MANIFEST})[/]"
        )
        return []

    console.print(f"[bold]Found {len(found)} package(s):[/]")
    for d in found:
        console.print(f"  - {os.path.basename(d)}")
    console.print()

    results = []
    for pkg_dir in found:
        name = os.path.basename(pkg_dir)
        ok = import_token(pkg_dir, interactive=interactive)
        results.append((name, ok))

    succeeded = sum(1 for _, ok in results if ok)
    console.print(f"\n[bold]Imported {succeeded}/{len(results)} token(s).[/]")
    return results


def import_token(source_path, interactive=True):
    """import a token from a local package directory.

    parameters:
        source_path — path to the token package directory
                      (must contain manifest.cinnamonint.json)
        interactive — if False, skip approval prompts (for testing)

    returns:
        True if import succeeded, False otherwise.
    """
    source_path = os.path.abspath(source_path)

    # --- validate package structure ---
    manifest_path = os.path.join(source_path, _MANIFEST)
    handler_path  = os.path.join(source_path, _HANDLER)

    if not os.path.exists(manifest_path):
        console.print(f"[red]Missing required file: [bold]{_MANIFEST}[/bold][/]")
        return False
    if not os.path.exists(handler_path):
        console.print(f"[red]Missing required file: [bold]{_HANDLER}[/bold][/]")
        return False

    # --- parse manifest ---
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]Invalid {_MANIFEST}: {e}[/]")
        return False

    name = manifest.get("name", "").strip()
    if not name:
        console.print(f"[red]{_MANIFEST} missing 'name' field.[/]")
        return False

    aliases  = manifest.get("aliases", [])
    category = manifest.get("category", "other").strip() or "other"
    priority = int(manifest.get("priority", 1))
    author   = manifest.get("author", "unknown")

    # --- conflict check (before touching any files) ---
    conflicts = _check_conflicts(name, aliases)
    if conflicts:
        console.print("[red bold]Import blocked — conflicts found:[/]")
        for c in conflicts:
            console.print(f"  [red]✗[/] {c}")
        return False

    # --- read handler source ---
    with open(handler_path, "r") as f:
        handler_source = f.read()

    # --- check for test file (optional) ---
    test_src = os.path.join(source_path, _TEST)
    has_test = os.path.exists(test_src)

    # --- display metadata ---
    console.print("\n[bold]Token Import Review[/]")
    console.print(f"  Name:       [bold]{name}[/]")
    console.print(f"  Author:     [bold]{author}[/]")
    console.print(f"  Category:   {category}")
    console.print(f"  Priority:   {priority}")
    console.print(f"  Aliases:    {', '.join(aliases) if aliases else '(none)'}")

    flags = []
    if manifest.get("destructive"):
        flags.append("[red bold]DESTRUCTIVE[/]")
    if manifest.get("downloads"):
        flags.append("[yellow bold]DOWNLOADS[/]")
    if manifest.get("uploads"):
        flags.append("[yellow bold]UPLOADS[/]")
    if flags:
        console.print(f"  Flags:      {' '.join(flags)}")
    console.print(f"  Test file:  {'included' if has_test else 'none'}")
    console.print()

    # --- static analysis ---
    findings = analyze_handler_code(handler_source)
    detected_flags = auto_detect_flags(handler_source)

    # collect flag mismatches (warnings + prompts shown after code review)
    flag_mismatches = []
    if detected_flags["destructive"] and not manifest.get("destructive"):
        flag_mismatches.append(("destructive", "red"))
    if detected_flags["downloads"] and not manifest.get("downloads"):
        flag_mismatches.append(("downloads", "yellow"))
    if detected_flags["uploads"] and not manifest.get("uploads"):
        flag_mismatches.append(("uploads", "yellow"))

    console.print("[bold]Handler Code:[/]")
    display_code_with_findings(handler_source, findings)
    console.print()

    # --- category confirmation (interactive) ---
    if interactive:
        answer = console.input(
            f"[cyan]Category [[bold]{category}[/bold]] "
            f"(press Enter to accept or type a new one): [/]"
        ).strip()
        if answer:
            category = answer

    # --- flag decision prompts (warning + prompt together, after code review) ---
    user_flag_decisions = {"destructive": False, "downloads": False, "uploads": False}
    if interactive:
        for flag, color in flag_mismatches:
            console.print(
                f"[{color} bold]WARNING:[/] handler contains {flag} patterns "
                f"but manifest does not flag it as {flag}!"
            )
            answer = console.input(
                f"[yellow]Mark as {flag}? [y/N]: [/]"
            ).strip().lower()
            user_flag_decisions[flag] = answer in ("y", "yes")
    else:
        # non-interactive: sandbox detections default to True (safe fallback)
        for flag, _ in flag_mismatches:
            user_flag_decisions[flag] = True

    # --- check for extract_operands on flagged tokens ---
    is_flagged = (manifest.get("destructive") or manifest.get("downloads")
                  or manifest.get("uploads") or user_flag_decisions["destructive"]
                  or user_flag_decisions["downloads"] or user_flag_decisions["uploads"])
    if is_flagged and not has_extract_operands(handler_source):
        console.print(
            "[yellow bold]WARNING:[/] this token is flagged but does not implement "
            "[bold]extract_operands(sentence)[/]. The approval system will fall "
            "back to full-sentence hashing, which may prompt redundantly for the "
            "same operation in different sentences."
        )

    # --- user approval ---
    if interactive:
        console.print(
            f"[yellow]This code was written by '[bold]{author}[/bold]'. "
            f"Review carefully for malicious behavior.[/]"
        )
        answer = console.input(
            "[yellow]Approve import? [y/N]: [/]"
        ).strip().lower()
        if answer not in ("y", "yes"):
            console.print("[dim]Import rejected.[/]")
            log_learning_event(
                name, "import_rejected",
                details=json.dumps({"author": author, "source": source_path}),
                source=f"local:{source_path}",
            )
            return False

    # --- copy handler file to tokens/<category>/<name>.py ---
    dest_dir = os.path.join(TOKENS_DIR, category)
    os.makedirs(dest_dir, exist_ok=True)

    # create __init__.py if needed
    init_path = os.path.join(dest_dir, "__init__.py")
    if not os.path.exists(init_path):
        open(init_path, "w").close()

    dest_handler = os.path.join(dest_dir, f"{name}.py")
    try:
        shutil.copy2(handler_path, dest_handler)
    except OSError as e:
        console.print(f"[red]Failed to copy handler file: {e}[/]")
        _rollback(name, dest_handler, None)
        return False

    rel_handler = os.path.relpath(dest_handler, PROJECT_ROOT)

    # --- copy test file to tests/<category>/test_<name>.py ---
    test_file_path = None
    rel_test = None
    if has_test:
        test_dir = os.path.join(TESTS_DIR, category)
        os.makedirs(test_dir, exist_ok=True)
        test_file_path = os.path.join(test_dir, f"test_{name}.py")
        try:
            shutil.copy2(test_src, test_file_path)
        except OSError as e:
            console.print(f"[red]Failed to copy test file: {e}[/]")
            _rollback(name, dest_handler, test_file_path)
            return False
        rel_test = os.path.relpath(test_file_path, PROJECT_ROOT)
        console.print(f"[dim]Test file written: {rel_test}[/]")

    # --- run tests (after copying so imports resolve) ---
    if has_test:
        console.print("[bold]Running import tests...[/]")
        pass_count, fail_count = _run_import_tests(test_file_path)
        if fail_count > 0:
            console.print(
                f"[red]{fail_count} test(s) failed. Import aborted.[/]"
            )
            _rollback(name, dest_handler, test_file_path)
            return False
        console.print(f"[green]{pass_count} test(s) passed.[/]")

    # --- register in DB ---
    final_destructive = manifest.get("destructive", False) or user_flag_decisions["destructive"]
    final_downloads   = manifest.get("downloads",   False) or user_flag_decisions["downloads"]
    final_uploads     = manifest.get("uploads",     False) or user_flag_decisions["uploads"]

    token_id = None
    try:
        token_id = add_token(
            name=name,
            category=category,
            priority=priority,
            handler_path=rel_handler,
            aliases=aliases,
            destructive=final_destructive,
            downloads=final_downloads,
            uploads=final_uploads,
            author=author,
            source="import",
            version=manifest.get("version", "1.0.0"),
            test_path=rel_test,
        )

    except Exception as e:
        # rollback: remove handler file + test file (DB entry auto-rolled back
        # on exception if not committed, but add_token uses context manager so
        # we remove manually if token_id was assigned)
        console.print(f"[red]Registration failed: {e}[/]")
        _rollback(name, dest_handler, test_file_path)
        return False

    # --- log the import ---
    log_learning_event(
        name, "import",
        details=json.dumps({
            "author": author,
            "category": category,
            "aliases": aliases,
            "has_tests": has_test,
            "source": source_path,
        }),
        source=f"local:{source_path}",
    )

    console.print(
        f"[green bold]Token '[bold]{name}[/bold]' imported successfully![/]"
    )
    return True


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _check_conflicts(name, aliases):
    """return a list of conflict description strings (empty = no conflicts)."""
    conflicts = []

    existing = get_token(name)
    if existing:
        conflicts.append(f"name '{name}' is already a registered token")

    existing_by_alias = get_token_by_alias(name)
    if existing_by_alias:
        conflicts.append(
            f"name '{name}' is already an alias of token '{existing_by_alias['name']}'"
        )

    for alias in aliases:
        tok = get_token(alias)
        if tok:
            conflicts.append(
                f"alias '{alias}' is already a registered token name"
            )
            continue
        tok = get_token_by_alias(alias)
        if tok:
            conflicts.append(
                f"alias '{alias}' is already an alias of token '{tok['name']}'"
            )

    return conflicts


def _rollback(token_name, handler_file, test_file):
    """remove handler file, test file, and DB entry on import failure."""
    if handler_file and os.path.exists(handler_file):
        os.remove(handler_file)
        console.print(f"[dim]Rolled back handler file: {handler_file}[/]")

    if test_file and os.path.exists(test_file):
        os.remove(test_file)
        console.print(f"[dim]Rolled back test file: {test_file}[/]")

    if get_token(token_name):
        remove_token(token_name)
        console.print(f"[dim]Rolled back DB entry for '{token_name}'.[/]")


def _run_import_tests(test_file_path):
    """run the test file via subprocess + pytest.

    the handler and test file must already be copied to their final
    locations so imports resolve correctly.

    returns (pass_count, fail_count).
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file_path, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        console.print("[red]Tests timed out after 30 seconds.[/]")
        return 0, 1
    except Exception as e:
        console.print(f"[red]Failed to run tests: {e}[/]")
        return 0, 1

    # parse pytest output for pass/fail counts
    output = result.stdout + result.stderr
    pass_count = 0
    fail_count = 0

    for line in output.splitlines():
        line_stripped = line.strip()
        # pytest summary line: "3 passed", "1 failed, 2 passed", etc.
        if "passed" in line_stripped or "failed" in line_stripped:
            import re
            passed_match = re.search(r"(\d+) passed", line_stripped)
            failed_match = re.search(r"(\d+) failed", line_stripped)
            if passed_match:
                pass_count = int(passed_match.group(1))
            if failed_match:
                fail_count = int(failed_match.group(1))

    # if pytest itself failed to run (exit code != 0) but we found no
    # parsed counts, treat it as a single failure
    if result.returncode != 0 and pass_count == 0 and fail_count == 0:
        console.print(f"[red]pytest exited with code {result.returncode}:[/]")
        if output.strip():
            console.print(f"[dim]{output.strip()}[/]")
        return 0, 1

    # show verbose output on failures
    if fail_count > 0 and output.strip():
        console.print(f"[dim]{output.strip()}[/]")

    return pass_count, fail_count
