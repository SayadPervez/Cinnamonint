"""
Test suite for the approval system — store CRUD + approval logic.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.registry.store import (
    init_db,
    add_token,
    get_token,
    check_approval,
    store_approval,
    get_approvals_for_token,
    remove_approvals_for_token,
)
from src.safety.approvals import (
    compute_command_hash,
    compute_operand_hash,
    needs_approval,
    check_and_approve,
)


def setUpModule():
    from src.config import settings
    settings.DB_DIR = os.path.join(settings.PROJECT_ROOT, "db")
    settings.REGISTRY_DB = os.path.join(settings.DB_DIR, "registry.db")
    init_db()


class test_approval_store(unittest.TestCase):
    """test the approval CRUD functions in store.py."""

    def setUp(self):
        """ensure we have a token to work with."""
        self.token = get_token("plus")
        self.assertIsNotNone(self.token, "plus token must exist for tests")
        self.token_id = self.token["id"]
        # clean up any leftover approvals from previous runs
        remove_approvals_for_token(self.token_id)

    def tearDown(self):
        remove_approvals_for_token(self.token_id)

    def test_store_and_check(self):
        """storing an approval makes it checkable."""
        cmd_hash = compute_command_hash("plus", "5 plus 3")
        self.assertFalse(check_approval(self.token_id, cmd_hash))
        store_approval(self.token_id, cmd_hash, "5 plus 3")
        self.assertTrue(check_approval(self.token_id, cmd_hash))

    def test_different_sentences_different_hashes(self):
        """different sentences produce different approval entries."""
        h1 = compute_command_hash("plus", "5 plus 3")
        h2 = compute_command_hash("plus", "10 plus 20")
        self.assertNotEqual(h1, h2)
        store_approval(self.token_id, h1, "5 plus 3")
        self.assertTrue(check_approval(self.token_id, h1))
        self.assertFalse(check_approval(self.token_id, h2))

    def test_get_approvals_for_token(self):
        """listing approvals returns all stored entries."""
        h1 = compute_command_hash("plus", "a")
        h2 = compute_command_hash("plus", "b")
        store_approval(self.token_id, h1, "a")
        store_approval(self.token_id, h2, "b")
        approvals = get_approvals_for_token(self.token_id)
        self.assertEqual(len(approvals), 2)

    def test_remove_approvals(self):
        """removing approvals clears all entries for a token."""
        h = compute_command_hash("plus", "test")
        store_approval(self.token_id, h, "test")
        self.assertTrue(check_approval(self.token_id, h))
        remove_approvals_for_token(self.token_id)
        self.assertFalse(check_approval(self.token_id, h))

    def test_duplicate_store_ignored(self):
        """storing the same approval twice doesn't raise."""
        h = compute_command_hash("plus", "dup")
        store_approval(self.token_id, h, "dup")
        store_approval(self.token_id, h, "dup")  # should not raise
        approvals = get_approvals_for_token(self.token_id)
        self.assertEqual(len(approvals), 1)


class test_approval_logic(unittest.TestCase):
    """test the needs_approval and check_and_approve functions."""

    def test_normal_token_no_approval_needed(self):
        """non-flagged tokens (plus, say, etc.) don't need approval."""
        token = get_token("plus")
        self.assertFalse(needs_approval(token))

    def test_destructive_token_needs_approval(self):
        """destructive tokens always need approval."""
        fake_token = {"destructive": True, "downloads": False, "uploads": False}
        self.assertTrue(needs_approval(fake_token))

    def test_downloads_token_needs_approval(self):
        """download tokens need approval."""
        fake_token = {"destructive": False, "downloads": True, "uploads": False}
        self.assertTrue(needs_approval(fake_token))

    def test_normal_token_auto_approved(self):
        """check_and_approve returns True immediately for non-flagged tokens."""
        token = get_token("plus")
        result = check_and_approve(token, "5 plus 3", interactive=False)
        self.assertTrue(result)

    def test_hash_normalization(self):
        """hashes are consistent regardless of whitespace."""
        h1 = compute_command_hash("plus", "  5   plus   3  ")
        h2 = compute_command_hash("plus", "5 plus 3")
        self.assertEqual(h1, h2)

    def test_hash_case_insensitive(self):
        """hashes are case-insensitive."""
        h1 = compute_command_hash("PLUS", "5 PLUS 3")
        h2 = compute_command_hash("plus", "5 plus 3")
        self.assertEqual(h1, h2)


class test_operand_hash(unittest.TestCase):
    """test operand-based hashing for flagged tokens."""

    def test_operand_hash_basic(self):
        """operand hash produces consistent results."""
        h1 = compute_operand_hash("upload", "/images/trip", "drive")
        h2 = compute_operand_hash("upload", "/images/trip", "drive")
        self.assertEqual(h1, h2)

    def test_operand_hash_different_from_sentence_hash(self):
        """operand hash differs from sentence hash for the same token."""
        h_operand = compute_operand_hash("upload", "/images/trip", "drive")
        h_sentence = compute_command_hash("upload", "upload /images/trip to drive")
        self.assertNotEqual(h_operand, h_sentence)

    def test_operand_hash_same_across_sentences(self):
        """same operands from different sentences produce the same hash."""
        # both sentences resolve to the same (token, params, context)
        h1 = compute_operand_hash("upload", "/images/trip", "drive")
        h2 = compute_operand_hash("upload", "/images/trip", "drive")
        self.assertEqual(h1, h2)

    def test_operand_hash_case_insensitive(self):
        """operand hash is case-insensitive."""
        h1 = compute_operand_hash("UPLOAD", "/Images/Trip", "Drive")
        h2 = compute_operand_hash("upload", "/images/trip", "drive")
        self.assertEqual(h1, h2)

    def test_operand_hash_whitespace_normalized(self):
        """operand hash strips whitespace."""
        h1 = compute_operand_hash("  upload ", "  /images/trip  ", "  drive  ")
        h2 = compute_operand_hash("upload", "/images/trip", "drive")
        self.assertEqual(h1, h2)

    def test_operand_hash_empty_context(self):
        """operand hash handles empty context."""
        h1 = compute_operand_hash("delete", "/tmp/file", "")
        h2 = compute_operand_hash("delete", "/tmp/file", None)
        self.assertEqual(h1, h2)

    def test_operand_hash_different_params(self):
        """different parameters produce different hashes."""
        h1 = compute_operand_hash("upload", "/images/trip", "drive")
        h2 = compute_operand_hash("upload", "/images/vacation", "drive")
        self.assertNotEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()
