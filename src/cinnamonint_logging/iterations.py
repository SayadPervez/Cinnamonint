"""
Per-prompt iteration chain tracking — log each step of sentence reduction.
"""

import sqlite3
from src.config.settings import LOGS_DB, ITERATION_RETENTION_COUNT


def _connect():
    """open a connection to the logs database."""
    conn = sqlite3.connect(LOGS_DB)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def log_iteration(prompt_id, iteration_num, sentence_before,
                  token_processed, handler_path, sentence_after,
                  duration_ms):
    """record a single iteration of the reduction loop."""
    with _connect() as conn:
        conn.execute(
            """INSERT INTO iterations
               (prompt_id, iteration_num, sentence_before,
                token_processed, handler_path, sentence_after, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (prompt_id, iteration_num, sentence_before,
             token_processed, handler_path, sentence_after, duration_ms),
        )


def get_iterations(prompt_id):
    """return the full iteration chain for a given prompt."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM iterations
               WHERE prompt_id = ?
               ORDER BY iteration_num""",
            (prompt_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def prune_old_iterations():
    """delete iteration data for all but the most recent N prompts.

    keeps the prompt rows intact — only removes the detailed iteration chains.
    """
    with _connect() as conn:
        conn.execute(
            """DELETE FROM iterations
               WHERE prompt_id NOT IN (
                   SELECT id FROM prompts
                   ORDER BY timestamp DESC
                   LIMIT ?
               )""",
            (ITERATION_RETENTION_COUNT,),
        )
