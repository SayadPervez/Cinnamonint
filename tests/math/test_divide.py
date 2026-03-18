"""
Test suite for the 'divide' token handler.
"""

import unittest
from tokens.math.divide import handle


class test_divide(unittest.TestCase):

    def test_basic_division(self):
        self.assertEqual(handle("10 divide 2"), "5")

    def test_divide_by_form(self):
        self.assertEqual(handle("10 divide by 2"), "5")

    def test_chained_with_other_token(self):
        self.assertEqual(handle("20 divide 4 plus 3"), "5 plus 3")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_division_by_zero(self):
        self.assertEqual(handle("10 divide 0"), "10 divide 0")

    def test_decimal_result(self):
        self.assertEqual(handle("10 divide 3"), "3.3333333333333335")

    def test_no_left_number_form(self):
        self.assertEqual(handle("divide 10 by 2"), "5")

    def test_stops_at_token_boundary(self):
        """divide should not consume numbers past another token."""
        self.assertEqual(handle("divide 20 by 4 plus 3"), "5 plus 3")


if __name__ == "__main__":
    unittest.main()
