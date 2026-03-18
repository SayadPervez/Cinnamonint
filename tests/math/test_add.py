"""
Test suite for the 'add' token handler.
"""

import unittest
from tokens.math.add import handle


class test_add(unittest.TestCase):

    def test_basic_add(self):
        self.assertEqual(handle("3 add 5"), "8")

    def test_larger_numbers(self):
        self.assertEqual(handle("10 add 20"), "30")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_zero(self):
        self.assertEqual(handle("0 add 0"), "0")

    def test_stops_at_token_boundary(self):
        self.assertEqual(handle("add 7 and 9 plus 4 minus 10"), "16 plus 4 minus 10")

    def test_stops_at_subtract_boundary(self):
        self.assertEqual(handle("add 5 6 and subtract 3"), "11 subtract 3")

    def test_sum_all_when_no_boundary(self):
        self.assertEqual(handle("add 5 6 7"), "18")


if __name__ == "__main__":
    unittest.main()
