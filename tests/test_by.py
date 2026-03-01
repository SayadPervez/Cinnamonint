"""
Test suite for the 'by' token handler.
"""

import unittest
from tokens.math.by import handle


class test_by(unittest.TestCase):

    def test_basic_division(self):
        self.assertEqual(handle("10 by 2"), "5")

    def test_chained_with_other_token(self):
        self.assertEqual(handle("10 by 5 plus 3"), "2 plus 3")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_division_by_zero(self):
        self.assertEqual(handle("10 by 0"), "10 by 0")


if __name__ == "__main__":
    unittest.main()
