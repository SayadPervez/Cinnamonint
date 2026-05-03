"""
Test suite for the spell correction engine.
Tests token-only mode, full mode (with dictionary), suggestion ranking,
skip rules, and non-interactive passthrough.
"""

import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.engine.spellcheck import (
    _is_skippable,
    _is_known_word,
    _get_suggestions,
    _load_dictionary,
    spellcheck,
    reset_cache,
)


class test_skippable(unittest.TestCase):
    """test which words are skipped by spellcheck."""

    def test_empty_string(self):
        self.assertTrue(_is_skippable(""))

    def test_single_char(self):
        self.assertTrue(_is_skippable("a"))
        self.assertTrue(_is_skippable("5"))

    def test_number(self):
        self.assertTrue(_is_skippable("42"))
        self.assertTrue(_is_skippable("3.14"))
        self.assertTrue(_is_skippable("1,000"))

    def test_punctuation(self):
        self.assertTrue(_is_skippable("..."))
        self.assertTrue(_is_skippable("++"))
        self.assertTrue(_is_skippable("->"))

    def test_normal_word_not_skipped(self):
        self.assertFalse(_is_skippable("hello"))
        self.assertFalse(_is_skippable("plus"))
        self.assertFalse(_is_skippable("subtract"))


class test_is_known_word(unittest.TestCase):
    """test word recognition against different sources."""

    def test_known_token(self):
        self.assertTrue(_is_known_word("plus", {"plus", "minus"}, None, set()))

    def test_known_alias(self):
        self.assertTrue(_is_known_word("add", {"add", "plus"}, None, set()))

    def test_known_english_word(self):
        english = {"hello", "world", "the"}
        self.assertTrue(_is_known_word("hello", set(), english, set()))

    def test_known_user_word(self):
        self.assertTrue(_is_known_word("xyzzy", set(), None, {"xyzzy"}))

    def test_unknown_word_no_dict(self):
        """in token-only mode, non-token words are unknown."""
        self.assertFalse(_is_known_word("hello", {"plus"}, None, set()))

    def test_unknown_word_with_dict(self):
        english = {"hello", "world"}
        self.assertFalse(_is_known_word("xyzzy", {"plus"}, english, set()))


class test_suggestions(unittest.TestCase):
    """test fuzzy matching for suggestions."""

    def test_close_match(self):
        tokens = ["plus", "minus", "subtract", "multiply", "divide"]
        matches = _get_suggestions("plsu", tokens)
        self.assertIn("plus", matches)

    def test_close_match_subtract(self):
        tokens = ["plus", "minus", "subtract", "multiply", "divide"]
        matches = _get_suggestions("subtarct", tokens)
        self.assertIn("subtract", matches)

    def test_no_close_match(self):
        tokens = ["plus", "minus", "subtract"]
        matches = _get_suggestions("xyzzy", tokens)
        self.assertEqual(len(matches), 0)

    def test_multiple_matches(self):
        tokens = ["plus", "pulse", "plug"]
        matches = _get_suggestions("plu", tokens)
        # should return at least one close match
        self.assertGreater(len(matches), 0)


class test_non_interactive(unittest.TestCase):
    """spellcheck in non-interactive mode (piped input) does nothing."""

    def test_passthrough(self):
        result = spellcheck("subtarct 5 from 10", interactive=False)
        self.assertEqual(result, "subtarct 5 from 10")

    def test_empty_input(self):
        result = spellcheck("", interactive=False)
        self.assertEqual(result, "")


class test_dictionary_loading(unittest.TestCase):
    """test dictionary file detection."""

    def test_no_dictionary_returns_none(self):
        """when words.txt is absent, returns None."""
        reset_cache()
        original = settings.DICTIONARY_FILE
        settings.DICTIONARY_FILE = "/tmp/nonexistent_words_file.txt"
        try:
            result = _load_dictionary()
            self.assertIsNone(result)
        finally:
            settings.DICTIONARY_FILE = original
            reset_cache()

    def test_dictionary_loads_words(self):
        """when words.txt exists, returns a set of words."""
        reset_cache()
        original = settings.DICTIONARY_FILE
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello\nworld\nthe\n")
            tmp_path = f.name
        settings.DICTIONARY_FILE = tmp_path
        try:
            result = _load_dictionary()
            self.assertIsNotNone(result)
            self.assertIn("hello", result)
            self.assertIn("world", result)
            self.assertEqual(len(result), 3)
        finally:
            settings.DICTIONARY_FILE = original
            os.unlink(tmp_path)
            reset_cache()

    def test_cache_works(self):
        """dictionary is loaded once and cached."""
        reset_cache()
        original = settings.DICTIONARY_FILE
        settings.DICTIONARY_FILE = "/tmp/nonexistent_words_file.txt"
        try:
            _load_dictionary()
            # second call should use cache, not re-check file
            result = _load_dictionary()
            self.assertIsNone(result)
        finally:
            settings.DICTIONARY_FILE = original
            reset_cache()


if __name__ == "__main__":
    unittest.main()
