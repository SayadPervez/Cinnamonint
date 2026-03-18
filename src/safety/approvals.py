"""
Command variation approval system.

Tracks which (token, command_variation) pairs the user has approved.
Destructive / download / upload tokens always require approval — every time.
Normal tokens are approved once per command variation and remembered.

For flagged tokens whose handler implements extract_operands(sentence),
the approval hash is based on the extracted (token, parameters, context)
tuple rather than the full sentence — so the same operation in different
sentences doesn't prompt twice.
"""

import hashlib

from rich.console import Console

from src.registry.store import (
    check_approval as _db_check,
    store_approval as _db_store,
    get_approvals_for_token as _db_get_approvals,
)
from src.registry.loader import load_handler as _load_handler

console = Console()


def compute_command_hash(token_name, sentence):
    """hash a normalized (token + sentence) pair into a command signature.

    normalization:
      - lowercase
      - collapse whitespace
      - strip leading/trailing whitespace
    """
    normalized = f"{token_name.lower()}:{' '.join(sentence.lower().split())}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_operand_hash(token_name, parameters, context):
    """hash a (token, parameters, context) tuple into a command signature.

    used for flagged handlers that implement extract_operands().
    this produces the same hash regardless of what else is in the sentence.
    """
    parts = [
        token_name.lower().strip(),
        parameters.lower().strip() if parameters else "",
        context.lower().strip() if context else "",
    ]
    normalized = ":".join(parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _try_extract_operands(handler_path, sentence):
    """attempt to call extract_operands() from a handler module.

    returns (token_name, parameters, context) on success, or None if the
    handler doesn't implement extract_operands.
    """
    try:
        module = _load_handler(handler_path, raw_module=True)
        extract_fn = getattr(module, "extract_operands", None)
        if extract_fn is None:
            return None
        result = extract_fn(sentence)
        if (isinstance(result, (tuple, list)) and len(result) == 3):
            return tuple(str(x) for x in result)
        return None
    except Exception:
        return None


def needs_approval(token):
    """return True if this token requires per-invocation approval.

    tokens flagged destructive / downloads / uploads always need approval.
    all other tokens are auto-approved (math, say, clear, etc.).
    """
    return bool(token.get("destructive") or
                token.get("downloads") or
                token.get("uploads"))


def check_and_approve(token, sentence, interactive=True):
    """check approval state for a (token, sentence) pair.

    for non-flagged tokens: always approved (returns True immediately).
    for flagged tokens:
      - try extract_operands() for operand-based hash (preferred)
      - fall back to full-sentence hash if not implemented
      - check the approval cache in the DB
      - if cached: inform user and return True
      - if not cached and interactive: prompt user
      - if not cached and non-interactive (piped): deny

    returns True if execution should proceed, False to skip.
    """
    if not needs_approval(token):
        return True

    token_id = token["id"]
    token_name = token["name"]
    handler_path = token.get("handler_path", "")

    # try operand-based hash first, fall back to sentence hash
    operands = _try_extract_operands(handler_path, sentence)
    if operands:
        cmd_hash = compute_operand_hash(*operands)
        display_text = f"{operands[0]} {operands[1]} {operands[2]}".strip()
    else:
        cmd_hash = compute_command_hash(token_name, sentence)
        display_text = sentence.strip()

    # check cache — always-approve tokens don't reach here,
    # but destructive tokens still need per-invocation confirmation
    if token.get("destructive"):
        # destructive tokens ALWAYS prompt, never cached
        pass
    else:
        # downloads / uploads: check cache
        cached = _db_check(token_id, cmd_hash)
        if cached:
            console.print(
                f"[dim]Running previously approved: [bold]{display_text}[/bold][/]"
            )
            return True

    if not interactive:
        console.print(
            f"[red]Approval required for '[bold]{token_name}[/bold]' — "
            f"cannot approve in non-interactive mode.[/]"
        )
        return False

    # build the prompt
    flags = []
    if token.get("destructive"):
        flags.append("[red bold]DESTRUCTIVE[/]")
    if token.get("downloads"):
        flags.append("[yellow bold]DOWNLOADS[/]")
    if token.get("uploads"):
        flags.append("[yellow bold]UPLOADS[/]")
    flag_text = " ".join(flags)

    console.print(
        f"\n{flag_text} — [bold]{token_name}[/]: "
        f"[cyan]{display_text}[/]"
    )
    answer = console.input("[yellow]Approve? [y/N]: [/]").strip().lower()

    if answer not in ("y", "yes"):
        console.print("[dim]Denied.[/]")
        return False

    # store approval for non-destructive flagged tokens
    if not token.get("destructive"):
        _db_store(token_id, cmd_hash, display_text)

    return True


def get_approvals(token_id):
    """list all approved command variations for a token."""
    return _db_get_approvals(token_id)
