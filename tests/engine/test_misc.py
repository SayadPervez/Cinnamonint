"""
Miscellaneous tests — edge cases, stall detection, mode enforcement.
"""

import unittest
import sys
import os
import subprocess
import stat

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.registry.store import init_db as init_registry
from src.cinnamonint_logging.logger import init_db as init_logs
from src.seed import seed
from src.engine.processor import process
from src.config import settings


def setUpModule():
    """ensure the DB is initialized and seeded before running tests."""
    settings.DB_DIR = os.path.join(settings.PROJECT_ROOT, "db")
    settings.REGISTRY_DB = os.path.join(settings.DB_DIR, "registry.db")
    settings.LOGS_DB = os.path.join(settings.DB_DIR, "logs.db")

    if not os.path.exists(settings.REGISTRY_DB):
        seed()


def _pipe(text):
    """run cinnamonint with piped input, return stdout."""
    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, "-m", "src.main"],
        input=text,
        capture_output=True,
        text=True,
        cwd=settings.PROJECT_ROOT,
        env=env,
    )
    return result.stdout.strip(), result.returncode


class test_stall_detection(unittest.TestCase):
    """engine should stop when a handler returns the sentence unchanged."""

    def test_no_numbers_for_add(self):
        result, iterations, status = process("add x and y")
        self.assertEqual(result, "add x and y")
        self.assertEqual(status, "ok")
        self.assertLessEqual(iterations, 1)

    def test_no_numbers_for_plus(self):
        result, iterations, status = process("x plus y")
        self.assertEqual(result, "x plus y")
        self.assertLessEqual(iterations, 1)

    def test_no_numbers_for_minus(self):
        result, iterations, status = process("foo minus bar")
        self.assertEqual(result, "foo minus bar")
        self.assertLessEqual(iterations, 1)

    def test_no_numbers_for_multiply(self):
        result, iterations, status = process("multiply nothing")
        self.assertEqual(result, "multiply nothing")
        self.assertLessEqual(iterations, 1)


class test_piped_mode_enforcement(unittest.TestCase):
    """piped input must respect the same gates as the REPL."""

    def test_learn_blocked_via_pipe(self):
        out, _ = _pipe("learn subtract")
        # during an active learn session, the handover guard fires first;
        # otherwise, the token-exists check fires. both are valid rejections.
        handover_active = os.path.exists(
            os.path.join(settings.PROJECT_ROOT, ".learn_handover.json")
        )
        if handover_active:
            self.assertIn("pending learn session", out.lower())
        else:
            self.assertIn("already a registered token", out.lower())

    def test_forget_blocked_via_pipe(self):
        out, _ = _pipe("forget nonexistent_token_xyz")
        self.assertIn("not found", out.lower())

    def test_logs_command_via_pipe(self):
        out, _ = _pipe("logs recent")
        # should produce log output (table or "no prompts"), not treat as sentence
        self.assertNotIn("logs recent", out.lower().split("\n")[-1:])

    def test_exit_via_pipe(self):
        out, _ = _pipe("exit")
        self.assertIn("goodbye", out.lower())

    def test_normal_sentence_via_pipe(self):
        out, _ = _pipe("5 plus 3")
        self.assertEqual(out, "8")


class test_hardened_mode_via_pipe(unittest.TestCase):
    """hardened mode (read-only registry) must block learn/forget via pipe."""

    def setUp(self):
        """make registry.db read-only to simulate hardened mode."""
        self._registry = settings.REGISTRY_DB
        self._original_mode = os.stat(self._registry).st_mode
        os.chmod(self._registry, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def tearDown(self):
        """restore original permissions."""
        os.chmod(self._registry, self._original_mode)

    def test_learn_blocked_in_hardened_pipe(self):
        out, _ = _pipe("learn subtract")
        self.assertIn("hardened", out.lower())

    def test_forget_blocked_in_hardened_pipe(self):
        out, _ = _pipe("forget subtract")
        self.assertIn("hardened", out.lower())

    def test_normal_sentence_works_in_hardened_pipe(self):
        out, _ = _pipe("5 plus 3")
        self.assertEqual(out, "8")


if __name__ == "__main__":
    unittest.main()
