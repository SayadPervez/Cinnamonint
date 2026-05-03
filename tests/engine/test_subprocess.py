"""
Test suite for subprocess handler isolation.
Tests execution in both subprocess and direct modes, timeout enforcement,
crash handling, and output capture.
"""

import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.registry.loader import execute_handler, _execute_subprocess, _execute_direct


# --- helper: create a temporary handler file ---

def _write_temp_handler(code):
    """write handler code to a temp .py file inside tokens/ and return relative path."""
    tokens_dir = os.path.join(settings.PROJECT_ROOT, "tokens")
    fd, abs_path = tempfile.mkstemp(suffix=".py", dir=tokens_dir, prefix="_test_handler_")
    os.write(fd, code.encode())
    os.close(fd)
    rel_path = os.path.relpath(abs_path, settings.PROJECT_ROOT)
    return rel_path, abs_path


class test_subprocess_basic(unittest.TestCase):
    """basic handler execution via subprocess."""

    def setUp(self):
        self.handler_code = (
            "def handle(sentence):\n"
            "    return sentence.replace('hello', 'world')\n"
        )
        self.handler_path, self.abs_path = _write_temp_handler(self.handler_code)

    def tearDown(self):
        os.unlink(self.abs_path)

    def test_subprocess_returns_correct_result(self):
        """handler executed in subprocess returns expected output."""
        result = _execute_subprocess(self.handler_path, "hello there")
        self.assertEqual(result, "world there")

    def test_direct_returns_correct_result(self):
        """handler executed directly returns expected output."""
        result = _execute_direct(self.handler_path, "hello there")
        self.assertEqual(result, "world there")

    def test_execute_handler_respects_mode_subprocess(self):
        """execute_handler uses subprocess mode when configured."""
        original = settings.HANDLER_EXECUTION_MODE
        settings.HANDLER_EXECUTION_MODE = "subprocess"
        try:
            result = execute_handler(self.handler_path, "hello there")
            self.assertEqual(result, "world there")
        finally:
            settings.HANDLER_EXECUTION_MODE = original

    def test_execute_handler_respects_mode_direct(self):
        """execute_handler uses direct mode when configured."""
        original = settings.HANDLER_EXECUTION_MODE
        settings.HANDLER_EXECUTION_MODE = "direct"
        try:
            result = execute_handler(self.handler_path, "hello there")
            self.assertEqual(result, "world there")
        finally:
            settings.HANDLER_EXECUTION_MODE = original


class test_subprocess_timeout(unittest.TestCase):
    """timeout enforcement in subprocess mode."""

    def setUp(self):
        self.handler_code = (
            "import time\n"
            "def handle(sentence):\n"
            "    time.sleep(30)\n"
            "    return sentence\n"
        )
        self.handler_path, self.abs_path = _write_temp_handler(self.handler_code)
        # use a short timeout for testing
        self.original_timeout = settings.HANDLER_TIMEOUT_SECONDS
        settings.HANDLER_TIMEOUT_SECONDS = 1

    def tearDown(self):
        settings.HANDLER_TIMEOUT_SECONDS = self.original_timeout
        os.unlink(self.abs_path)

    def test_timeout_raises_runtime_error(self):
        """handler that exceeds timeout raises RuntimeError."""
        with self.assertRaises(RuntimeError) as ctx:
            _execute_subprocess(self.handler_path, "test input")
        self.assertIn("timed out", str(ctx.exception))


class test_subprocess_crash(unittest.TestCase):
    """crash handling in subprocess mode."""

    def setUp(self):
        self.handler_code = (
            "def handle(sentence):\n"
            "    raise ValueError('intentional crash')\n"
        )
        self.handler_path, self.abs_path = _write_temp_handler(self.handler_code)

    def tearDown(self):
        os.unlink(self.abs_path)

    def test_crash_raises_runtime_error(self):
        """handler that raises an exception produces RuntimeError."""
        with self.assertRaises(RuntimeError) as ctx:
            _execute_subprocess(self.handler_path, "test input")
        self.assertIn("crashed", str(ctx.exception))
        self.assertIn("intentional crash", str(ctx.exception))


class test_subprocess_missing_handler(unittest.TestCase):
    """missing handler file detection."""

    def test_subprocess_missing_file(self):
        """subprocess mode raises FileNotFoundError for missing handler."""
        with self.assertRaises(FileNotFoundError):
            _execute_subprocess("tokens/nonexistent/fake.py", "test")

    def test_direct_missing_file(self):
        """direct mode raises FileNotFoundError for missing handler."""
        with self.assertRaises(FileNotFoundError):
            _execute_direct("tokens/nonexistent/fake.py", "test")


class test_subprocess_no_handle_function(unittest.TestCase):
    """handler file without handle() function."""

    def setUp(self):
        self.handler_code = (
            "def not_handle(sentence):\n"
            "    return sentence\n"
        )
        self.handler_path, self.abs_path = _write_temp_handler(self.handler_code)

    def tearDown(self):
        os.unlink(self.abs_path)

    def test_subprocess_no_handle_raises(self):
        """subprocess mode raises RuntimeError when handle() is missing."""
        with self.assertRaises(RuntimeError) as ctx:
            _execute_subprocess(self.handler_path, "test")
        self.assertIn("cannot import name 'handle'", str(ctx.exception).lower())

    def test_direct_no_handle_raises(self):
        """direct mode raises AttributeError when handle() is missing."""
        with self.assertRaises(AttributeError):
            _execute_direct(self.handler_path, "test")


class test_subprocess_multiline_output(unittest.TestCase):
    """handler that returns multiline or whitespace-heavy results."""

    def setUp(self):
        self.handler_code = (
            "def handle(sentence):\n"
            "    return 'line1\\nline2\\nline3'\n"
        )
        self.handler_path, self.abs_path = _write_temp_handler(self.handler_code)

    def tearDown(self):
        os.unlink(self.abs_path)

    def test_preserves_multiline_output(self):
        """subprocess correctly captures multiline handler output."""
        result = _execute_subprocess(self.handler_path, "anything")
        self.assertEqual(result, "line1\nline2\nline3")


class test_subprocess_stdin_special_chars(unittest.TestCase):
    """handler receives special characters in sentence via stdin."""

    def setUp(self):
        self.handler_code = (
            "def handle(sentence):\n"
            "    return sentence\n"
        )
        self.handler_path, self.abs_path = _write_temp_handler(self.handler_code)

    def tearDown(self):
        os.unlink(self.abs_path)

    def test_quotes_in_sentence(self):
        """subprocess handles quotes in sentence correctly."""
        result = _execute_subprocess(self.handler_path, 'say "hello world"')
        self.assertEqual(result, 'say "hello world"')

    def test_newlines_in_sentence(self):
        """subprocess handles newlines in input sentence."""
        result = _execute_subprocess(self.handler_path, "line1\nline2")
        self.assertEqual(result, "line1\nline2")

    def test_unicode_in_sentence(self):
        """subprocess handles unicode characters."""
        result = _execute_subprocess(self.handler_path, "café résumé naïve")
        self.assertEqual(result, "café résumé naïve")


if __name__ == "__main__":
    unittest.main()
