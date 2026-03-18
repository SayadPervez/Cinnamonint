"""
Token registry — SQLite CRUD operations for tokens and aliases.
"""

import sqlite3
import os
from src.config.settings import REGISTRY_DB, REGISTRY_SCHEMA


def _connect():
    """open a connection to the registry database with FK support."""
    conn = sqlite3.connect(REGISTRY_DB)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """create the registry database and tables from schema.sql."""
    os.makedirs(os.path.dirname(REGISTRY_DB), exist_ok=True)
    with _connect() as conn:
        with open(REGISTRY_SCHEMA, "r") as f:
            conn.executescript(f.read())


# ---------------------------------------------------------------------------
# token CRUD
# ---------------------------------------------------------------------------

def add_token(name, category, priority, handler_path, aliases=None,
              destructive=False, downloads=False, uploads=False,
              author="local", source="seed", version="1.0.0",
              test_path=None):
    """register a new token and its aliases. returns the token id."""
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO tokens
               (name, category, priority, handler_path, test_path, destructive,
                downloads, uploads, approved, author, source, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)""",
            (name, category, priority, handler_path, test_path,
             int(destructive), int(downloads), int(uploads),
             author, source, version),
        )
        token_id = cursor.lastrowid
        if aliases:
            for alias in aliases:
                conn.execute(
                    "INSERT INTO aliases (token_id, alias) VALUES (?, ?)",
                    (token_id, alias),
                )
        return token_id


def remove_token(name):
    """delete a token by name. cascades to aliases."""
    with _connect() as conn:
        conn.execute("DELETE FROM tokens WHERE name = ?", (name,))


def get_token(name):
    """look up a token by its canonical name. returns a dict or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM tokens WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None


def get_token_by_alias(alias):
    """look up a token by one of its aliases. returns a dict or None."""
    with _connect() as conn:
        row = conn.execute(
            """SELECT t.* FROM tokens t
               JOIN aliases a ON t.id = a.token_id
               WHERE a.alias = ?""",
            (alias,),
        ).fetchone()
        return dict(row) if row else None


def get_all_tokens():
    """return a list of dicts for every registered token."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tokens ORDER BY priority DESC, name"
        ).fetchall()
        return [dict(r) for r in rows]


def get_aliases(token_id):
    """return a list of alias strings for a given token id."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT alias FROM aliases WHERE token_id = ?", (token_id,)
        ).fetchall()
        return [r["alias"] for r in rows]


def get_all_keywords():
    """return a dict mapping every keyword (name + aliases) to its token dict.

    this is the primary lookup table used during sentence processing.
    """
    with _connect() as conn:
        tokens = conn.execute("SELECT * FROM tokens").fetchall()
        keyword_map = {}
        for row in tokens:
            token = dict(row)
            keyword_map[token["name"]] = token
            aliases = conn.execute(
                "SELECT alias FROM aliases WHERE token_id = ?",
                (token["id"],),
            ).fetchall()
            for a in aliases:
                keyword_map[a["alias"]] = token
        return keyword_map


def get_keywords_for_words(words):
    """return a keyword map for only the given words.

    single query: checks words against both tokens.name and aliases.alias.
    returns a dict mapping matched keywords to their token dicts,
    identical in structure to get_all_keywords() but only for matches.
    """
    if not words:
        return {}

    unique = list(set(w.lower() for w in words))
    placeholders = ", ".join("?" for _ in unique)

    with _connect() as conn:
        # find tokens whose name matches any word
        name_rows = conn.execute(
            f"SELECT * FROM tokens WHERE name IN ({placeholders})",
            unique,
        ).fetchall()

        # find tokens whose alias matches any word
        alias_rows = conn.execute(
            f"""SELECT t.*, a.alias FROM tokens t
                JOIN aliases a ON t.id = a.token_id
                WHERE a.alias IN ({placeholders})""",
            unique,
        ).fetchall()

        keyword_map = {}

        for row in name_rows:
            token = dict(row)
            keyword_map[token["name"]] = token

        for row in alias_rows:
            token = dict(row)
            alias = token.pop("alias")
            keyword_map[alias] = token

        return keyword_map


def token_exists(name):
    """check whether a token name or alias is already registered."""
    if get_token(name):
        return True
    if get_token_by_alias(name):
        return True
    return False


# ---------------------------------------------------------------------------
# approvals
# ---------------------------------------------------------------------------

def check_approval(token_id, command_hash):
    """return True if this (token_id, command_hash) pair has been approved."""
    with _connect() as conn:
        row = conn.execute(
            """SELECT id FROM approvals
               WHERE token_id = ? AND command_hash = ?""",
            (token_id, command_hash),
        ).fetchone()
        return row is not None


def store_approval(token_id, command_hash, command_display):
    """record an approved (token_id, command_hash) pair."""
    with _connect() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO approvals
               (token_id, command_hash, command_display)
               VALUES (?, ?, ?)""",
            (token_id, command_hash, command_display),
        )


def get_approvals_for_token(token_id):
    """return all approved command variations for a token."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT command_display, approved_at FROM approvals
               WHERE token_id = ?
               ORDER BY approved_at DESC""",
            (token_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def remove_approvals_for_token(token_id):
    """delete all approvals for a token (used when unlearning)."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM approvals WHERE token_id = ?", (token_id,),
        )
