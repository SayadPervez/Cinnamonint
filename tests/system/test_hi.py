"""
Test suite for the 'hi' token handler (greetings).
"""

import unittest
from unittest.mock import patch
from tokens.system.hi import handle, GREETINGS


class test_hi(unittest.TestCase):

    def test_hi_returns_remainder(self):
        """'hi multiply 5 and 6' -> 'multiply 5 and 6'."""
        result = handle("hi multiply 5 and 6")
        self.assertEqual(result, "multiply 5 and 6")

    def test_hi_alone(self):
        """'hi' alone -> empty string."""
        result = handle("hi")
        self.assertEqual(result, "")

    def test_alias_hey(self):
        """'hey world' -> 'world'."""
        result = handle("hey world")
        self.assertEqual(result, "world")

    def test_alias_hey_there(self):
        """'hey there' matches multi-word alias, returns empty."""
        result = handle("hey there")
        self.assertEqual(result, "")

    def test_alias_hello(self):
        """'hello world' -> 'world'."""
        result = handle("hello world")
        self.assertEqual(result, "world")

    def test_alias_greetings(self):
        """'greetings everyone' -> 'everyone'."""
        result = handle("greetings everyone")
        self.assertEqual(result, "everyone")

    def test_alias_howdy(self):
        """'howdy partner' -> 'partner'."""
        result = handle("howdy partner")
        self.assertEqual(result, "partner")

    def test_alias_sup(self):
        """'sup dude' -> 'dude'."""
        result = handle("sup dude")
        self.assertEqual(result, "dude")

    def test_greeting_printed(self, ):
        """stdout should contain one of the preset greetings."""
        with patch("builtins.print") as mock_print:
            handle("hi")
            mock_print.assert_called_once()
            printed = mock_print.call_args[0][0]
            self.assertIn(printed, GREETINGS)

    def test_no_match(self):
        """'high five' should NOT match (word boundary)."""
        result = handle("high five")
        self.assertEqual(result, "high five")

    def test_case_insensitive(self):
        """'HI there' -> 'there'."""
        result = handle("HI there")
        self.assertEqual(result, "there")

    def test_mid_sentence(self):
        """'say hi to everyone' -> 'say to everyone' + greeting printed."""
        with patch("builtins.print") as mock_print:
            result = handle("say hi to everyone")
            self.assertEqual(result, "say to everyone")
            mock_print.assert_called_once()
            printed = mock_print.call_args[0][0]
            self.assertIn(printed, GREETINGS)

    def test_no_greeting_printed_on_no_match(self):
        """no greeting printed when keyword absent."""
        with patch("builtins.print") as mock_print:
            handle("nothing here")
            mock_print.assert_not_called()


if __name__ == "__main__":
    unittest.main()
