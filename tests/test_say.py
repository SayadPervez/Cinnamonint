"""
Test suite for the 'say' token handler.
"""

import unittest
from tokens.system.say import handle


class test_say(unittest.TestCase):

    def test_basic_say(self):
        self.assertEqual(handle("say hello world"), "hello world")

    def test_single_word(self):
        self.assertEqual(handle("say goodbye"), "goodbye")

    def test_no_keyword(self):
        self.assertEqual(handle("hello world"), "hello world")

    def test_say_with_preceding_text(self):
        self.assertEqual(handle("please say hello"), "please hello")


if __name__ == "__main__":
    unittest.main()
