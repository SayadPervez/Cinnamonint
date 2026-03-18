"""
Test suite for combinational sentences — multi-token interactions
where tokens must defer to each other correctly.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.registry.store import init_db as init_registry
from src.cinnamonint_logging.logger import init_db as init_logs
from src.seed import seed
from src.engine.processor import process


def setUpModule():
    """ensure the DB is initialized and seeded before running tests."""
    from src.config import settings
    settings.DB_DIR = os.path.join(settings.PROJECT_ROOT, "db")
    settings.REGISTRY_DB = os.path.join(settings.DB_DIR, "registry.db")
    settings.LOGS_DB = os.path.join(settings.DB_DIR, "logs.db")

    if not os.path.exists(settings.REGISTRY_DB):
        seed()


class test_add_multiply_subtract(unittest.TestCase):
    """add X and Y multiply by Z subtract W — all variants should agree."""

    def test_with_it_filler(self):
        """add 5 and 6 multiply it by 11 and subtract 21 -> 100."""
        result, _, status = process(
            "add 5 and 6 multiply it by 11 and subtract 21"
        )
        self.assertEqual(result, "100")
        self.assertEqual(status, "ok")

    def test_with_and_separator(self):
        """add 5 and 6 and multiply by 11 and subtract 21 -> 100."""
        result, _, status = process(
            "add 5 and 6 and multiply by 11 and subtract 21"
        )
        self.assertEqual(result, "100")
        self.assertEqual(status, "ok")

    def test_without_separator(self):
        """add 5 and 6 multiply by 11 and subtract 21 -> 100."""
        result, _, status = process(
            "add 5 and 6 multiply by 11 and subtract 21"
        )
        self.assertEqual(result, "100")
        self.assertEqual(status, "ok")


class test_bodmas_preserved(unittest.TestCase):
    """BODMAS ordering must still work for plain binary forms."""

    def test_plus_then_multiply(self):
        """3 plus 5 multiply 2 -> 13 (BODMAS: 5*2=10, 3+10=13)."""
        result, _, status = process("3 plus 5 multiply 2")
        self.assertEqual(result, "13")
        self.assertEqual(status, "ok")

    def test_plus_then_into(self):
        """3 plus 5 into 2 -> 13 (same as multiply)."""
        result, _, status = process("3 plus 5 into 2")
        self.assertEqual(result, "13")
        self.assertEqual(status, "ok")

    def test_minus_then_multiply(self):
        """10 minus 2 multiply 3 -> 4 (BODMAS: 2*3=6, 10-6=4)."""
        result, _, status = process("10 minus 2 multiply 3")
        self.assertEqual(result, "4")
        self.assertEqual(status, "ok")


class test_skip_on_stall(unittest.TestCase):
    """engine should skip stalled tokens and try next priority."""

    def test_multiply_defers_then_add_runs(self):
        """when multiply can't find operands, add should run first."""
        result, iterations, status = process(
            "add 10 and 20 multiply by 3"
        )
        self.assertEqual(result, "90")
        self.assertEqual(status, "ok")
        # multiply stalls + by stalls + add runs + multiply runs = 4 iterations
        self.assertGreaterEqual(iterations, 3)

    def test_multiply_defers_with_them_filler(self):
        """multiply them by X defers to the left token."""
        result, _, status = process(
            "add 2 and 3 multiply them by 10"
        )
        self.assertEqual(result, "50")
        self.assertEqual(status, "ok")

    def test_chained_multiply_and_subtract(self):
        """add then multiply then subtract in sequence."""
        result, _, status = process(
            "add 1 and 2 and 3 multiply it by 2 and subtract 2"
        )
        self.assertEqual(result, "10")
        self.assertEqual(status, "ok")


if __name__ == "__main__":
    unittest.main()
