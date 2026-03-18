"""
Test suite for the 'subtract' token handler.
"""

import unittest
from tokens.math.subtract import handle


class test_subtract(unittest.TestCase):

    def test_basic_subtract(self):
        self.assertEqual(handle("10 subtract 3"), "7")

    def test_subtract_from_form(self):
        self.assertEqual(handle("subtract 3 from 10"), "7")

    def test_chained_with_other_token(self):
        self.assertEqual(handle("20 subtract 5 plus 3"), "15 plus 3")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_negative_result(self):
        self.assertEqual(handle("3 subtract 10"), "-7")


if __name__ == "__main__":
    unittest.main()
