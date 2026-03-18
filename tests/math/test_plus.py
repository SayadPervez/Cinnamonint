"""
Test suite for the 'plus' token handler.
"""

import unittest
from tokens.math.plus import handle


class test_plus(unittest.TestCase):

    def test_basic_addition(self):
        self.assertEqual(handle("5 plus 3"), "8")

    def test_larger_numbers(self):
        self.assertEqual(handle("10 plus 20"), "30")

    def test_decimal_addition(self):
        self.assertEqual(handle("1.5 plus 2.5"), "4")

    def test_chained_with_other_token(self):
        self.assertEqual(handle("5 plus 3 minus 1"), "8 minus 1")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_negative_result(self):
        self.assertEqual(handle("-5 plus 3"), "-2")

    def test_zero(self):
        self.assertEqual(handle("0 plus 0"), "0")

    def test_only_takes_last_left_number(self):
        """plus should only take the immediately preceding number, not all left numbers."""
        self.assertEqual(handle("10 hello 5 plus 3"), "10 hello 8")


if __name__ == "__main__":
    unittest.main()
