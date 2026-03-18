"""
Seed the token registry with built-in tokens.
Run this once during setup to populate registry.db.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.registry.store import add_token, get_token, init_db
from src.cinnamonint_logging.logger import init_db as init_logs_db


# ---------------------------------------------------------------------------
# built-in token definitions
# ---------------------------------------------------------------------------

BUILTIN_TOKENS = [
    {
        "name": "plus",
        "category": "math",
        "priority": 2,
        "handler_path": "tokens/math/plus.py",
        "test_path": "tests/math/test_plus.py",
        "aliases": ["+"],
    },
    {
        "name": "minus",
        "category": "math",
        "priority": 2,
        "handler_path": "tokens/math/minus.py",
        "test_path": "tests/math/test_minus.py",
        "aliases": [],
    },
    {
        "name": "add",
        "category": "math",
        "priority": 2,
        "handler_path": "tokens/math/add.py",
        "test_path": "tests/math/test_add.py",
        "aliases": [],
    },
    {
        "name": "subtract",
        "category": "math",
        "priority": 2,
        "handler_path": "tokens/math/subtract.py",
        "test_path": "tests/math/test_subtract.py",
        "aliases": [],
    },
    {
        "name": "multiply",
        "category": "math",
        "priority": 3,
        "handler_path": "tokens/math/multiply.py",
        "test_path": "tests/math/test_multiply.py",
        "aliases": ["multiplied"],
    },
    {
        "name": "divide",
        "category": "math",
        "priority": 3,
        "handler_path": "tokens/math/divide.py",
        "test_path": "tests/math/test_divide.py",
        "aliases": [],
    },
    {
        "name": "into",
        "category": "math",
        "priority": 3,
        "handler_path": "tokens/math/into.py",
        "test_path": "tests/math/test_into.py",
        "aliases": [],
    },
    {
        "name": "by",
        "category": "math",
        "priority": 3,
        "handler_path": "tokens/math/by.py",
        "test_path": "tests/math/test_by.py",
        "aliases": [],
    },
    {
        "name": "say",
        "category": "system",
        "priority": 1,
        "handler_path": "tokens/system/say.py",
        "test_path": "tests/system/test_say.py",
        "aliases": ["speak", "tell"],
    },
    {
        "name": "exit",
        "category": "system",
        "priority": 0,
        "handler_path": "tokens/system/exit.py",
        "test_path": None,
        "aliases": ["quit", "q"],
    },
    {
        "name": "time",
        "category": "utility",
        "priority": 1,
        "handler_path": "tokens/utility/time.py",
        "test_path": None,
        "aliases": [],
    },
    {
        "name": "date",
        "category": "utility",
        "priority": 1,
        "handler_path": "tokens/utility/date.py",
        "test_path": None,
        "aliases": ["today"],
    },
    {
        "name": "now",
        "category": "utility",
        "priority": 1,
        "handler_path": "tokens/utility/now.py",
        "test_path": None,
        "aliases": [],
    },
    {
        "name": "clear",
        "category": "system",
        "priority": 1,
        "handler_path": "tokens/system/clear.py",
        "test_path": "tests/system/test_clear.py",
        "aliases": ["cls", "clrscr"],
    },
]


def seed():
    """register all built-in tokens if they don't already exist."""
    init_db()
    init_logs_db()

    for token_def in BUILTIN_TOKENS:
        if get_token(token_def["name"]):
            continue

        add_token(
            name=token_def["name"],
            category=token_def["category"],
            priority=token_def["priority"],
            handler_path=token_def["handler_path"],
            aliases=token_def["aliases"],
            test_path=token_def["test_path"],
            source="seed",
        )

    print(f"seeded {len(BUILTIN_TOKENS)} tokens into registry.")


if __name__ == "__main__":
    seed()
