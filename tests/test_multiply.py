"""
Test suite for the 'multiply' token handler.
"""

import unittest
from tokens.math.multiply import handle


class test_multiply(unittest.TestCase):

    def test_basic_multiplication(self):
        self.assertEqual(handle("5 multiply 3"), "15")

    def test_multiplied_by_form(self):
        self.assertEqual(handle("5 multiplied by 3"), "15")

    def test_chained_with_other_token(self):
        self.assertEqual(handle("4 multiply 5 plus 2"), "20 plus 2")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_zero_multiply(self):
        self.assertEqual(handle("5 multiply 0"), "0")

    def test_decimal(self):
        self.assertEqual(handle("2.5 multiply 4"), "10")

    def test_stops_at_token_boundary(self):
        """multiply should not consume numbers past another token."""
        self.assertEqual(handle("multiply 2 3 4 plus 5"), "24 plus 5")

    def test_stops_at_divide_boundary(self):
        self.assertEqual(handle("multiply 2 2 and 4 divide by 8"), "16 divide by 8")

    def test_stops_at_divide_boundary_with_and(self):
        self.assertEqual(handle("multiply 2 2 and 4 and divide by 8"), "16 divide by 8")

    def test_multi_number_no_boundary(self):
        self.assertEqual(handle("multiply 2, 3 and 4"), "24")


if __name__ == "__main__":
    unittest.main()
