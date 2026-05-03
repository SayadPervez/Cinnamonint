"""
Test suite for the user dictionary — add, remove, list, persist.
"""

import unittest
import sys
import os
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.engine.user_dictionary import (
    load_user_words, add_word, remove_word, list_words,
    load_corrections, add_correction, remove_correction, list_corrections,
)


class test_user_dictionary(unittest.TestCase):
    """test user dictionary CRUD operations."""

    def setUp(self):
        """redirect user dictionary to a temp file."""
        self.original_file = settings.USER_DICTIONARY_FILE
        self.original_dir = settings.DATA_DIR
        self.tmp_dir = tempfile.mkdtemp()
        settings.DATA_DIR = self.tmp_dir
        settings.USER_DICTIONARY_FILE = os.path.join(self.tmp_dir, "user_dictionary.json")

    def tearDown(self):
        """restore original settings and clean up."""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        settings.USER_DICTIONARY_FILE = self.original_file
        settings.DATA_DIR = self.original_dir

    def test_empty_on_missing_file(self):
        """loading from a nonexistent file returns empty set."""
        words = load_user_words()
        self.assertEqual(words, set())

    def test_add_word(self):
        """adding a word persists it to file."""
        add_word("hello")
        words = load_user_words()
        self.assertIn("hello", words)

    def test_add_duplicate(self):
        """adding the same word twice doesn't duplicate."""
        add_word("hello")
        add_word("hello")
        import json as _json
        with open(settings.USER_DICTIONARY_FILE) as f:
            words = _json.load(f)
        self.assertEqual(words.count("hello"), 1)

    def test_add_case_insensitive(self):
        """words are stored lowercase."""
        add_word("HeLLo")
        words = load_user_words()
        self.assertIn("hello", words)
        self.assertNotIn("HeLLo", words)

    def test_add_empty_ignored(self):
        """adding empty string does nothing."""
        add_word("")
        add_word("   ")
        words = load_user_words()
        self.assertEqual(words, set())

    def test_remove_word(self):
        """removing a word takes it out of the file."""
        add_word("hello")
        add_word("world")
        result = remove_word("hello")
        self.assertTrue(result)
        words = load_user_words()
        self.assertNotIn("hello", words)
        self.assertIn("world", words)

    def test_remove_nonexistent(self):
        """removing a nonexistent word returns False."""
        result = remove_word("nonexistent")
        self.assertFalse(result)

    def test_list_words_sorted(self):
        """list_words returns sorted output."""
        add_word("zebra")
        add_word("apple")
        add_word("mango")
        result = list_words()
        self.assertEqual(result, ["apple", "mango", "zebra"])

    def test_list_empty(self):
        """list_words on empty dictionary returns empty list."""
        result = list_words()
        self.assertEqual(result, [])

    def test_persistence_across_loads(self):
        """words survive reload from disk."""
        add_word("persist")
        # simulate fresh load
        words = load_user_words()
        self.assertIn("persist", words)


class test_corrections(unittest.TestCase):
    """test remembered corrections CRUD."""

    def setUp(self):
        self.original_file = settings.CORRECTIONS_FILE
        self.original_dir = settings.DATA_DIR
        self.tmp_dir = tempfile.mkdtemp()
        settings.DATA_DIR = self.tmp_dir
        settings.CORRECTIONS_FILE = os.path.join(self.tmp_dir, "corrections.json")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        settings.CORRECTIONS_FILE = self.original_file
        settings.DATA_DIR = self.original_dir

    def test_empty_on_missing_file(self):
        corrections = load_corrections()
        self.assertEqual(corrections, {})

    def test_add_correction(self):
        add_correction("subtrcat", "subtract")
        corrections = load_corrections()
        self.assertEqual(corrections["subtrcat"], "subtract")

    def test_overwrite_correction(self):
        add_correction("plsu", "plus")
        add_correction("plsu", "pulse")
        corrections = load_corrections()
        self.assertEqual(corrections["plsu"], "pulse")

    def test_remove_correction(self):
        add_correction("subtrcat", "subtract")
        result = remove_correction("subtrcat")
        self.assertTrue(result)
        corrections = load_corrections()
        self.assertNotIn("subtrcat", corrections)

    def test_remove_nonexistent(self):
        result = remove_correction("nope")
        self.assertFalse(result)

    def test_list_corrections_sorted(self):
        add_correction("zz", "z")
        add_correction("aa", "a")
        result = list_corrections()
        self.assertEqual(result, [("aa", "a"), ("zz", "z")])

    def test_case_insensitive(self):
        add_correction("PLSU", "PLUS")
        corrections = load_corrections()
        self.assertIn("plsu", corrections)
        self.assertEqual(corrections["plsu"], "plus")


if __name__ == "__main__":
    unittest.main()
