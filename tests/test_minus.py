"""
Test suite for the 'minus' token handler.
"""

import unittest
from tokens.math.minus import handle


class test_minus(unittest.TestCase):

    def test_basic_subtraction(self):
        self.assertEqual(handle("10 minus 3"), "7")

    def test_larger_numbers(self):
        self.assertEqual(handle("100 minus 50"), "50")

    def test_decimal_subtraction(self):
        self.assertEqual(handle("5.5 minus 2.5"), "3")

    def test_chained_with_other_token(self):
        self.assertEqual(handle("10 minus 3 plus 2"), "7 plus 2")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_negative_result(self):
        self.assertEqual(handle("3 minus 10"), "-7")

    def test_zero(self):
        self.assertEqual(handle("5 minus 5"), "0")


if __name__ == "__main__":
    unittest.main()
