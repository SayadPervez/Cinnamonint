"""
Core logging — prompts, results, learning events, execution log.
"""

import sqlite3
import os
from src.config.settings import LOGS_DB, LOGS_SCHEMA


def _connect():
    """open a connection to the logs database."""
    conn = sqlite3.connect(LOGS_DB)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """create the logs database and tables from schema.sql."""
    os.makedirs(os.path.dirname(LOGS_DB), exist_ok=True)
    with _connect() as conn:
        with open(LOGS_SCHEMA, "r") as f:
            conn.executescript(f.read())


# ---------------------------------------------------------------------------
# prompt logging
# ---------------------------------------------------------------------------

def log_prompt(input_text, final_output, iteration_count, status="ok"):
    """record a processed prompt and its result. returns the prompt id."""
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO prompts
               (input_text, final_output, iteration_count, status)
               VALUES (?, ?, ?, ?)""",
            (input_text, final_output, iteration_count, status),
        )
        return cursor.lastrowid


def get_recent_prompts(limit=20):
    """return the N most recent prompts."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM prompts ORDER BY timestamp DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def search_prompts(query):
    """search prompts by input text (substring match)."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM prompts
               WHERE input_text LIKE ?
               ORDER BY timestamp DESC""",
            (f"%{query}%",),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# learning events
# ---------------------------------------------------------------------------

def log_learning_event(token_name, action, details=None, source="local"):
    """record a learning event (learn, unlearn, import, update)."""
    with _connect() as conn:
        conn.execute(
            """INSERT INTO learning_events
               (token_name, action, details, source)
               VALUES (?, ?, ?, ?)""",
            (token_name, action, details, source),
        )


def get_learning_events():
    """return all learning events."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM learning_events ORDER BY timestamp DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# execution log
# ---------------------------------------------------------------------------

def log_execution(token_name, action_type, prompt_id=None,
                  command=None, path=None, url=None,
                  exit_code=None, details=None):
    """record a system execution event."""
    with _connect() as conn:
        conn.execute(
            """INSERT INTO execution_log
               (prompt_id, token_name, action_type, command, path, url,
                exit_code, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (prompt_id, token_name, action_type, command, path, url,
             exit_code, details),
        )


def get_recent_executions(limit=20):
    """return the N most recent execution log entries."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM execution_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_executions_for_prompt(prompt_id):
    """return execution log entries for a specific prompt."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM execution_log
               WHERE prompt_id = ?
               ORDER BY timestamp""",
            (prompt_id,),
        ).fetchall()
        return [dict(r) for r in rows]
