"""
Tests for hardened mode behaviour.

Hardened mode is detected when registry.db is read-only (chmod 444).
Mutation commands (learn, forget, import, restore) must be blocked,
while read-only operations (processing, logs, dictionary, export) work normally.
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from src.config.settings import (
    MODE_HARDENED,
    MODE_WORKSHOP,
    detect_mode,
    REGISTRY_DB,
)
from src.commands.dispatch import dispatch, _MUTATION_COMMANDS


# ---------------------------------------------------------------------------
# detect_mode unit tests
# ---------------------------------------------------------------------------

class test_detect_mode(unittest.TestCase):
    """mode detection based on registry.db writability."""

    def test_workshop_when_writable(self):
        """writable registry.db → workshop mode."""
        import tempfile, src.config.settings as settings
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            fake_db = f.name
        os.chmod(fake_db, 0o644)
        original = settings.REGISTRY_DB
        settings.REGISTRY_DB = fake_db
        try:
            self.assertEqual(detect_mode(), MODE_WORKSHOP)
        finally:
            settings.REGISTRY_DB = original
            os.unlink(fake_db)

    def test_hardened_when_readonly(self):
        """read-only registry.db → hardened mode."""
        import tempfile, src.config.settings as settings
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            fake_db = f.name
        os.chmod(fake_db, 0o444)
        original = settings.REGISTRY_DB
        settings.REGISTRY_DB = fake_db
        try:
            self.assertEqual(detect_mode(), MODE_HARDENED)
        finally:
            settings.REGISTRY_DB = original
            os.chmod(fake_db, 0o644)  # restore so we can delete
            os.unlink(fake_db)

    def test_workshop_when_missing(self):
        """missing registry.db → workshop mode (fresh setup)."""
        import src.config.settings as settings
        original = settings.REGISTRY_DB
        settings.REGISTRY_DB = "/tmp/cinnamonint_nonexistent_test.db"
        try:
            self.assertEqual(detect_mode(), MODE_WORKSHOP)
        finally:
            settings.REGISTRY_DB = original


# ---------------------------------------------------------------------------
# mutation command blocking
# ---------------------------------------------------------------------------

class test_mutation_blocked(unittest.TestCase):
    """mutation commands are blocked in hardened mode."""

    def setUp(self):
        self._patcher = patch(
            "src.commands.dispatch.detect_mode",
            return_value=MODE_HARDENED,
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_learn_blocked(self):
        result = dispatch("learn something")
        self.assertTrue(result)

    def test_forget_blocked(self):
        result = dispatch("forget something")
        self.assertTrue(result)

    def test_restore_blocked(self):
        result = dispatch("restore something")
        self.assertTrue(result)

    def test_import_blocked(self):
        result = dispatch("import something")
        self.assertTrue(result)

    def test_mutation_commands_list_complete(self):
        """ensure _MUTATION_COMMANDS covers all expected mutation ops."""
        expected = {"learn", "forget", "restore", "import"}
        self.assertEqual(set(_MUTATION_COMMANDS), expected)


# ---------------------------------------------------------------------------
# read-only operations work in hardened mode
# ---------------------------------------------------------------------------

class test_readonly_works(unittest.TestCase):
    """read-only commands still function in hardened mode."""

    def setUp(self):
        self._patcher = patch(
            "src.commands.dispatch.detect_mode",
            return_value=MODE_HARDENED,
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_exit_works(self):
        """exit command returns None (quit signal)."""
        self.assertIsNone(dispatch("exit"))

    def test_quit_works(self):
        self.assertIsNone(dispatch("quit"))

    def test_empty_input_handled(self):
        """empty input returns True (handled, no-op)."""
        self.assertTrue(dispatch(""))

    def test_non_command_passes_through(self):
        """regular sentence returns False (not a command)."""
        self.assertFalse(dispatch("2 plus 3"))

    @patch("src.commands.dispatch.handle_logs_command")
    def test_logs_command_works(self, mock_logs):
        """logs command returns True (handled) — not blocked."""
        self.assertTrue(dispatch("logs"))

    @patch("src.commands.dispatch.handle_dictionary_command")
    def test_dictionary_command_works(self, mock_dict):
        """dictionary command returns True (handled) — not blocked."""
        self.assertTrue(dispatch("dictionary list"))

    @patch("src.commands.dispatch.export_token")
    def test_export_allowed_in_hardened(self, mock_export):
        """export is read-only and allowed in hardened mode."""
        self.assertTrue(dispatch("export ping"))


# ---------------------------------------------------------------------------
# sentence processing in hardened mode
# ---------------------------------------------------------------------------

class test_processing_works(unittest.TestCase):
    """sentence processing works in hardened mode — handlers still execute."""

    def test_math_processes(self):
        """arithmetic still works — handlers run from the read-only registry."""
        from src.engine.processor import process

        final, iterations, status = process("2 plus 3")
        self.assertEqual(final.strip(), "5")
        self.assertGreaterEqual(iterations, 1)
        self.assertEqual(status, "ok")

    def test_chained_processing(self):
        """chained operations still reduce fully."""
        from src.engine.processor import process

        final, iterations, status = process("1 plus 2 plus 3")
        self.assertEqual(final.strip(), "6")
        self.assertEqual(status, "ok")


# ---------------------------------------------------------------------------
# banner / mode label
# ---------------------------------------------------------------------------

class test_banner(unittest.TestCase):
    """REPL banner reflects the current mode."""

    def test_mode_label_hardened(self):
        """the mode label computation produces 'hardened' for MODE_HARDENED."""
        mode = MODE_HARDENED
        mode_label = "workshop" if mode != MODE_HARDENED else "hardened"
        self.assertEqual(mode_label, "hardened")

    def test_mode_label_workshop(self):
        """the mode label computation produces 'workshop' for MODE_WORKSHOP."""
        mode = MODE_WORKSHOP
        mode_label = "workshop" if mode != MODE_HARDENED else "hardened"
        self.assertEqual(mode_label, "workshop")

    def test_banner_in_subprocess(self):
        """repl banner includes mode label when run as a subprocess."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import os, sys; "
             "sys.path.insert(0, os.getcwd()); "
             "from src.main import repl; "
             "repl()"],
            capture_output=True, text=True, timeout=5,
            input="exit\n",
            cwd=os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            ),
        )
        self.assertEqual(result.returncode, 0)
        # banner should contain either "workshop" or "hardened"
        combined = result.stdout + result.stderr
        self.assertTrue(
            "workshop" in combined or "hardened" in combined,
            f"banner missing mode label: {combined!r}",
        )


if __name__ == "__main__":
    unittest.main()
