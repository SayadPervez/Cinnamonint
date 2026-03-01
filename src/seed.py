"""
Seed the token registry with built-in tokens.
Run this once during setup to populate registry.db.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.registry.store import add_token, add_test_case, get_token, init_db
from src.aif_logging.logger import init_db as init_logs_db


# ---------------------------------------------------------------------------
# built-in token definitions
# ---------------------------------------------------------------------------

BUILTIN_TOKENS = [
    {
        "name": "plus",
        "category": "math",
        "priority": 2,
        "handler_path": "tokens/math/plus.py",
        "aliases": ["+"],
        "tests": [
            ("5 plus 3", "8", "basic addition"),
            ("10 plus 20", "30", "larger numbers"),
            ("1.5 plus 2.5", "4", "decimal addition"),
            ("5 plus 3 minus 1", "8 minus 1", "chained with minus"),
        ],
    },
    {
        "name": "minus",
        "category": "math",
        "priority": 2,
        "handler_path": "tokens/math/minus.py",
        "aliases": [],
        "tests": [
            ("10 minus 3", "7", "basic subtraction"),
            ("100 minus 50", "50", "larger numbers"),
            ("5.5 minus 2.5", "3", "decimal subtraction"),
            ("10 minus 3 plus 2", "7 plus 2", "chained with plus"),
        ],
    },
    {
        "name": "add",
        "category": "math",
        "priority": 2,
        "handler_path": "tokens/math/add.py",
        "aliases": [],
        "tests": [
            ("3 add 5", "8", "basic add"),
            ("10 add 20", "30", "larger add"),
        ],
    },
    {
        "name": "subtract",
        "category": "math",
        "priority": 2,
        "handler_path": "tokens/math/subtract.py",
        "aliases": [],
        "tests": [
            ("10 subtract 3", "7", "basic subtract"),
            ("subtract 3 from 10", "7", "subtract X from Y form"),
            ("20 subtract 5 plus 3", "15 plus 3", "chained with plus"),
        ],
    },
    {
        "name": "multiply",
        "category": "math",
        "priority": 3,
        "handler_path": "tokens/math/multiply.py",
        "aliases": ["multiplied"],
        "tests": [
            ("5 multiply 3", "15", "basic multiplication"),
            ("5 multiplied by 3", "15", "multiplied by form"),
            ("4 multiply 5 plus 2", "20 plus 2", "chained with plus"),
        ],
    },
    {
        "name": "divide",
        "category": "math",
        "priority": 3,
        "handler_path": "tokens/math/divide.py",
        "aliases": [],
        "tests": [
            ("10 divide 2", "5", "basic division"),
            ("10 divide by 2", "5", "divide by form"),
            ("20 divide 4 plus 3", "5 plus 3", "chained with plus"),
        ],
    },
    {
        "name": "into",
        "category": "math",
        "priority": 3,
        "handler_path": "tokens/math/into.py",
        "aliases": [],
        "tests": [
            ("5 into 6", "30", "basic multiplication via into"),
            ("5 into 6 plus 2", "30 plus 2", "chained with plus"),
        ],
    },
    {
        "name": "by",
        "category": "math",
        "priority": 3,
        "handler_path": "tokens/math/by.py",
        "aliases": [],
        "tests": [
            ("10 by 2", "5", "basic division via by"),
            ("10 by 5 plus 3", "2 plus 3", "chained with plus"),
        ],
    },
    {
        "name": "say",
        "category": "system",
        "priority": 1,
        "handler_path": "tokens/system/say.py",
        "aliases": ["speak", "tell"],
        "tests": [
            ("say hello world", "hello world", "basic say"),
            ("say goodbye", "goodbye", "single word"),
        ],
    },
    {
        "name": "exit",
        "category": "system",
        "priority": 0,
        "handler_path": "tokens/system/exit.py",
        "aliases": ["quit", "q"],
        "tests": [],
    },
    {
        "name": "time",
        "category": "utility",
        "priority": 1,
        "handler_path": "tokens/utility/time.py",
        "aliases": [],
        "tests": [],  # time is dynamic — no static test cases
    },
    {
        "name": "date",
        "category": "utility",
        "priority": 1,
        "handler_path": "tokens/utility/date.py",
        "aliases": ["today"],
        "tests": [],  # date is dynamic
    },
    {
        "name": "now",
        "category": "utility",
        "priority": 1,
        "handler_path": "tokens/utility/now.py",
        "aliases": [],
        "tests": [],  # dynamic
    },
    {
        "name": "clear",
        "category": "system",
        "priority": 1,
        "handler_path": "tokens/system/clear.py",
        "aliases": ["cls", "clrscr"],
        "tests": [],  # side-effect only — clears terminal
    },
]


def seed():
    """register all built-in tokens if they don't already exist."""
    init_db()
    init_logs_db()

    for token_def in BUILTIN_TOKENS:
        if get_token(token_def["name"]):
            continue

        token_id = add_token(
            name=token_def["name"],
            category=token_def["category"],
            priority=token_def["priority"],
            handler_path=token_def["handler_path"],
            aliases=token_def["aliases"],
        )

        for test in token_def["tests"]:
            input_sentence, expected_output, description = test
            add_test_case(token_id, input_sentence, expected_output, description)

    print(f"seeded {len(BUILTIN_TOKENS)} tokens into registry.")


if __name__ == "__main__":
    seed()
