"""
Test suite for the engine — integration tests for the full reduction loop.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.registry.store import init_db as init_registry
from src.aif_logging.logger import init_db as init_logs
from src.seed import seed
from src.engine.processor import process


def setUpModule():
    """ensure the DB is initialized and seeded before running tests."""
    # use test databases
    from src.config import settings
    settings.DB_DIR = os.path.join(settings.PROJECT_ROOT, "db")
    settings.REGISTRY_DB = os.path.join(settings.DB_DIR, "registry.db")
    settings.LOGS_DB = os.path.join(settings.DB_DIR, "logs.db")

    if not os.path.exists(settings.REGISTRY_DB):
        seed()


class test_engine_math(unittest.TestCase):
    """test the full reduction loop with math operations."""

    def test_simple_addition(self):
        result, iterations, status = process("5 plus 3")
        self.assertEqual(result, "8")
        self.assertEqual(status, "ok")
        self.assertGreater(iterations, 0)

    def test_simple_subtraction(self):
        result, _, status = process("10 minus 3")
        self.assertEqual(result, "7")
        self.assertEqual(status, "ok")

    def test_multiplication(self):
        result, _, status = process("5 multiply 3")
        self.assertEqual(result, "15")
        self.assertEqual(status, "ok")

    def test_division(self):
        result, _, status = process("10 divide 2")
        self.assertEqual(result, "5")
        self.assertEqual(status, "ok")

    def test_chained_same_priority(self):
        """5 plus 3 minus 1: plus first (left-to-right), then minus."""
        result, iterations, status = process("5 plus 3 minus 1")
        self.assertEqual(result, "7")
        self.assertEqual(status, "ok")
        self.assertEqual(iterations, 2)

    def test_priority_ordering(self):
        """3 plus 5 multiply 2: multiply first (priority 3), then plus."""
        result, iterations, status = process("3 plus 5 multiply 2")
        self.assertEqual(result, "13")
        self.assertEqual(status, "ok")
        self.assertEqual(iterations, 2)

    def test_into(self):
        result, _, status = process("5 into 6")
        self.assertEqual(result, "30")
        self.assertEqual(status, "ok")

    def test_by(self):
        result, _, status = process("10 by 2")
        self.assertEqual(result, "5")
        self.assertEqual(status, "ok")

    def test_subtract_from(self):
        result, _, status = process("subtract 3 from 10")
        self.assertEqual(result, "7")
        self.assertEqual(status, "ok")

    def test_multiply_boundary_with_divide(self):
        """multiply 2 2 and 4 divide by 8 should give 2."""
        result, iterations, status = process("multiply 2 2 and 4 divide by 8")
        self.assertEqual(result, "2")
        self.assertEqual(status, "ok")
        self.assertEqual(iterations, 2)

    def test_multiply_boundary_with_and_divide(self):
        """multiply 2 2 and 4 and divide by 8 should give 2."""
        result, iterations, status = process("multiply 2 2 and 4 and divide by 8")
        self.assertEqual(result, "2")
        self.assertEqual(status, "ok")

    def test_add_boundary_with_subtract(self):
        """add should not consume numbers past subtract."""
        result, _, status = process("add 7 and 9 plus 4 minus 10")
        self.assertEqual(result, "10")
        self.assertEqual(status, "ok")


class test_engine_system(unittest.TestCase):
    """test system tokens."""

    def test_say(self):
        result, _, status = process("say hello world")
        self.assertEqual(result, "hello world")
        self.assertEqual(status, "ok")


class test_engine_no_tokens(unittest.TestCase):
    """test sentences with no recognized tokens."""

    def test_plain_text(self):
        result, iterations, status = process("hello world")
        self.assertEqual(result, "hello world")
        self.assertEqual(iterations, 0)
        self.assertEqual(status, "ok")

    def test_empty_string(self):
        result, iterations, status = process("")
        self.assertEqual(result, "")
        self.assertEqual(iterations, 0)


if __name__ == "__main__":
    unittest.main()
