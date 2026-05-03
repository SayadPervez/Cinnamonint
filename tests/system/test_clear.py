"""
Tests for the clear/cls/clrscr token handler.
"""

import unittest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tokens.system.clear import handle


class test_clear(unittest.TestCase):
    """test the clear handler."""

    @patch("os.close")
    @patch("os.write")
    @patch("os.open", return_value=99)
    def test_clear_alone(self, mock_open, mock_write, mock_close):
        result = handle("clear")
        self.assertEqual(result, "")
        mock_open.assert_called_once()

    @patch("os.close")
    @patch("os.write")
    @patch("os.open", return_value=99)
    def test_cls_alone(self, mock_open, mock_write, mock_close):
        result = handle("cls")
        self.assertEqual(result, "")
        mock_open.assert_called_once()

    @patch("os.close")
    @patch("os.write")
    @patch("os.open", return_value=99)
    def test_clrscr_alone(self, mock_open, mock_write, mock_close):
        result = handle("clrscr")
        self.assertEqual(result, "")
        mock_open.assert_called_once()

    @patch("os.close")
    @patch("os.write")
    @patch("os.open", return_value=99)
    def test_clear_with_text_before(self, mock_open, mock_write, mock_close):
        result = handle("hello clear")
        self.assertEqual(result, "hello")
        mock_open.assert_called_once()

    @patch("os.close")
    @patch("os.write")
    @patch("os.open", return_value=99)
    def test_clear_with_text_after(self, mock_open, mock_write, mock_close):
        result = handle("clear world")
        self.assertEqual(result, "world")
        mock_open.assert_called_once()

    @patch("os.close")
    @patch("os.write")
    @patch("os.open", return_value=99)
    def test_no_keyword(self, mock_open, mock_write, mock_close):
        result = handle("hello world")
        self.assertEqual(result, "hello world")
        mock_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
