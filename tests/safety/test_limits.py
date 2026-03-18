"""
Test suite for the iteration limit module.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.safety.limits import check_iteration_limit
from src.config import settings


class test_limits(unittest.TestCase):
    """test iteration limit logic."""

    def test_under_soft_limit(self):
        """iterations under 50 always continue."""
        ok, status = check_iteration_limit(10, "test", None)
        self.assertTrue(ok)
        self.assertIsNone(status)

    def test_at_hard_limit(self):
        """at hard limit, always stops."""
        ok, status = check_iteration_limit(
            settings.HARD_ITERATION_LIMIT, "test", None
        )
        self.assertFalse(ok)
        self.assertEqual(status, "limit_reached")

    def test_soft_limit_user_continues(self):
        """at soft limit, if callback says yes, continue."""
        def allow(iteration, sentence):
            return True

        ok, status = check_iteration_limit(
            settings.SOFT_ITERATION_LIMIT, "test", allow
        )
        self.assertTrue(ok)
        self.assertIsNone(status)

    def test_soft_limit_user_stops(self):
        """at soft limit, if callback says no, stop."""
        def deny(iteration, sentence):
            return False

        ok, status = check_iteration_limit(
            settings.SOFT_ITERATION_LIMIT, "test", deny
        )
        self.assertFalse(ok)
        self.assertEqual(status, "limit_reached")

    def test_soft_limit_no_callback(self):
        """at soft limit with no callback, continue."""
        ok, status = check_iteration_limit(
            settings.SOFT_ITERATION_LIMIT, "test", None
        )
        self.assertTrue(ok)
        self.assertIsNone(status)

    def test_zero_iteration(self):
        """iteration 0 always continues (no limits hit)."""
        ok, status = check_iteration_limit(0, "test", None)
        self.assertTrue(ok)
        self.assertIsNone(status)


if __name__ == "__main__":
    unittest.main()
