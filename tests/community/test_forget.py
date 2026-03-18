"""
Test suite for the forget command.
"""

import unittest
import sys
import os
import json
import shutil
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.registry.store import (
    init_db as init_registry,
    get_token,
    get_token_by_alias,
    get_aliases,
    remove_token,
    token_exists,
    add_token,
)
from src.cinnamonint_logging.logger import (
    init_db as init_logs,
    get_learning_events,
)
from src.community.forget import forget_token
from src.community.importer import import_token
from src.config.settings import (
    PROJECT_ROOT,
    TESTS_DIR,
    TOKEN_ARCHIVE_DIR,
    TOKENS_DIR,
)
from src.seed import seed


def setUpModule():
    from src.config import settings
    settings.DB_DIR = os.path.join(settings.PROJECT_ROOT, "db")
    settings.REGISTRY_DB = os.path.join(settings.DB_DIR, "registry.db")
    settings.LOGS_DB = os.path.join(settings.DB_DIR, "logs.db")

    if not os.path.exists(settings.REGISTRY_DB):
        seed()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_package(base_dir, name="forgettable", handler_code=None, test_file=None,
                  aliases=None, category="utility", priority=1):
    """create a minimal cinnamonint token package directory."""
    pkg_dir = os.path.join(base_dir, name)
    os.makedirs(pkg_dir, exist_ok=True)

    if handler_code is None:
        handler_code = (
            "import re\n\n"
            "def handle(sentence):\n"
            '    """dummy handler for testing."""\n'
            f"    keyword = {repr(name)}\n"
            "    lower = sentence.lower()\n"
            "    idx = lower.find(keyword)\n"
            "    if idx == -1:\n"
            "        return sentence\n"
            "    return (sentence[:idx] + sentence[idx + len(keyword):]).strip()\n"
        )

    manifest = {
        "name": name,
        "aliases": aliases or [],
        "category": category,
        "priority": priority,
        "destructive": False,
        "downloads": False,
        "uploads": False,
        "author": "test_suite",
        "version": "1.0.0",
    }

    with open(os.path.join(pkg_dir, "manifest.cinnamonint.json"), "w") as f:
        json.dump(manifest, f)

    with open(os.path.join(pkg_dir, "handler.cinnamonint.py"), "w") as f:
        f.write(handler_code)

    if test_file is not None:
        with open(os.path.join(pkg_dir, "test.cinnamonint.py"), "w") as f:
            f.write(test_file)

    return pkg_dir


def _cleanup_token(name, category=None):
    """remove a token from DB + files, for test isolation."""
    token = get_token(name)
    if token:
        handler_abs = os.path.join(PROJECT_ROOT, token["handler_path"])
        if os.path.exists(handler_abs):
            os.remove(handler_abs)
        remove_token(name)
    if category:
        test_file = os.path.join(TESTS_DIR, category, f"test_{name}.py")
        if os.path.exists(test_file):
            os.remove(test_file)


def _make_test_content(name, category):
    """generate a minimal test .py file content for a token."""
    return (
        'import unittest\n'
        'import sys, os\n'
        'sys.path.insert(0, os.path.dirname(os.path.dirname(\n'
        '    os.path.dirname(os.path.abspath(__file__)))))\n'
        f'from tokens.{category}.{name} import handle\n\n'
        f'class test_{name}(unittest.TestCase):\n'
        '    def test_001(self):\n'
        f'        self.assertEqual(handle("hello {name}"), "hello")\n\n'
        'if __name__ == "__main__":\n'
        '    unittest.main()\n'
    )


def _import_disposable_token(tmpdir, name="forgettable", aliases=None, category="utility"):
    """import a token that we intend to forget in the test."""
    test_content = _make_test_content(name, category)
    pkg = _make_package(tmpdir, name=name, aliases=aliases, category=category,
                        test_file=test_content)
    result = import_token(pkg, interactive=False)
    return result


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class test_forget_basic(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="cinnamonint_test_forget_")
        self.tokens_to_clean = []

    def tearDown(self):
        for name, category in self.tokens_to_clean:
            _cleanup_token(name, category)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        # clean up archive dirs if created
        for entry in os.listdir(TOKEN_ARCHIVE_DIR) if os.path.isdir(TOKEN_ARCHIVE_DIR) else []:
            if entry.startswith("forgettable"):
                shutil.rmtree(os.path.join(TOKEN_ARCHIVE_DIR, entry), ignore_errors=True)

    def test_forget_removes_from_db(self):
        """forgetting a token removes it from the registry."""
        _import_disposable_token(self.tmpdir, name="forgettable1")
        self.assertIsNotNone(get_token("forgettable1"))

        result = forget_token("forgettable1", interactive=False)
        self.assertTrue(result)
        self.assertIsNone(get_token("forgettable1"))

    def test_forget_archives_full_package(self):
        """forgetting a token exports a full package to .token_archive/."""
        _import_disposable_token(self.tmpdir, name="forgettable2", category="utility")

        handler = os.path.join(TOKENS_DIR, "utility", "forgettable2.py")
        self.assertTrue(os.path.exists(handler))

        forget_token("forgettable2", interactive=False)

        # handler file deleted
        self.assertFalse(os.path.exists(handler))

        # full package archived
        archive_dir = os.path.join(TOKEN_ARCHIVE_DIR, "forgettable2")
        self.assertTrue(os.path.isdir(archive_dir))
        self.assertTrue(os.path.exists(
            os.path.join(archive_dir, "manifest.cinnamonint.json")))
        self.assertTrue(os.path.exists(
            os.path.join(archive_dir, "handler.cinnamonint.py")))

    def test_forget_deletes_test_file(self):
        """forgetting a token removes its test file from tests/<category>/."""
        _import_disposable_token(self.tmpdir, name="forgettable3", category="utility")

        test_file = os.path.join(TESTS_DIR, "utility", "test_forgettable3.py")
        self.assertTrue(os.path.exists(test_file))

        forget_token("forgettable3", interactive=False)
        self.assertFalse(os.path.exists(test_file))

    def test_forget_by_alias(self):
        """forgetting by alias resolves to the canonical token and removes it."""
        _import_disposable_token(
            self.tmpdir, name="forgettable4", aliases=["fgt4alias"],
            category="utility",
        )
        self.assertIsNotNone(get_token_by_alias("fgt4alias"))

        result = forget_token("fgt4alias", interactive=False)
        self.assertTrue(result)
        self.assertIsNone(get_token("forgettable4"))
        self.assertIsNone(get_token_by_alias("fgt4alias"))

    def test_forget_nonexistent_returns_false(self):
        """forgetting a token that doesn't exist returns False."""
        result = forget_token("no_such_token_xyz", interactive=False)
        self.assertFalse(result)

    def test_forget_logs_event(self):
        """forgetting a token creates a learning_event with action='forget'."""
        _import_disposable_token(self.tmpdir, name="forgettable5", category="utility")
        forget_token("forgettable5", interactive=False)

        events = get_learning_events()
        forget_events = [
            e for e in events
            if e["token_name"] == "forgettable5" and e["action"] == "forget"
        ]
        self.assertTrue(len(forget_events) >= 1)

    def test_forget_does_not_affect_other_tokens(self):
        """forgetting one token leaves other tokens intact."""
        # 'plus' is a built-in seeded token
        self.assertIsNotNone(get_token("plus"))

        _import_disposable_token(self.tmpdir, name="forgettable6", category="utility")
        forget_token("forgettable6", interactive=False)

        # plus is still there
        self.assertIsNotNone(get_token("plus"))

    def test_forget_seeded_token_blocked(self):
        """seeded tokens (source='seed') cannot be forgotten."""
        result = forget_token("plus", interactive=False)
        self.assertFalse(result)
        # plus must still exist
        self.assertIsNotNone(get_token("plus"))


if __name__ == "__main__":
    unittest.main()
