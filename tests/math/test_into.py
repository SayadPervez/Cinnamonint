"""
Test suite for the 'into' token handler.
"""

import unittest
from tokens.math.into import handle


class test_into(unittest.TestCase):

    def test_basic_multiplication(self):
        self.assertEqual(handle("5 into 6"), "30")

    def test_chained_with_other_token(self):
        self.assertEqual(handle("5 into 6 plus 2"), "30 plus 2")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_decimal(self):
        self.assertEqual(handle("2.5 into 4"), "10")


if __name__ == "__main__":
    unittest.main()
