"""
Test suite for the restore command.
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
    remove_token,
)
from src.cinnamonint_logging.logger import init_db as init_logs
from src.community.forget import forget_token
from src.community.restore import restore_token, list_archived_tokens
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

def _make_package(base_dir, name, handler_code=None, test_file=None,
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


def _cleanup_archive(name):
    """remove an archived token package."""
    archive_path = os.path.join(TOKEN_ARCHIVE_DIR, name)
    if os.path.isdir(archive_path):
        shutil.rmtree(archive_path)


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


def _import_and_forget(tmpdir, name, aliases=None, category="utility"):
    """import a token then forget it, so it ends up in the archive."""
    test_content = _make_test_content(name, category)
    pkg = _make_package(tmpdir, name=name, aliases=aliases, category=category,
                        test_file=test_content)
    import_token(pkg, interactive=False)
    forget_token(name, interactive=False)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class test_restore_basic(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="cinnamonint_test_restore_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for name in ("restorable1", "restorable2", "restorable3",
                      "restorable4", "restorable5"):
            _cleanup_token(name, "utility")
            _cleanup_archive(name)

    def test_restore_brings_token_back(self):
        """restoring an archived token re-registers it in the DB."""
        _import_and_forget(self.tmpdir, "restorable1")
        self.assertIsNone(get_token("restorable1"))

        result = restore_token("restorable1", interactive=False)
        self.assertTrue(result)
        self.assertIsNotNone(get_token("restorable1"))

    def test_restore_recreates_handler_file(self):
        """restoring an archived token creates the handler .py file."""
        _import_and_forget(self.tmpdir, "restorable2")
        handler = os.path.join(TOKENS_DIR, "utility", "restorable2.py")
        self.assertFalse(os.path.exists(handler))

        restore_token("restorable2", interactive=False)
        self.assertTrue(os.path.exists(handler))

    def test_restore_recreates_test_file(self):
        """restoring an archived token creates the test file."""
        _import_and_forget(self.tmpdir, "restorable3")
        test_file = os.path.join(TESTS_DIR, "utility", "test_restorable3.py")
        self.assertFalse(os.path.exists(test_file))

        restore_token("restorable3", interactive=False)
        self.assertTrue(os.path.exists(test_file))

    def test_restore_removes_archive(self):
        """after successful restore, the archive directory is deleted."""
        _import_and_forget(self.tmpdir, "restorable4")
        archive = os.path.join(TOKEN_ARCHIVE_DIR, "restorable4")
        self.assertTrue(os.path.isdir(archive))

        restore_token("restorable4", interactive=False)
        self.assertFalse(os.path.isdir(archive))

    def test_restore_nonexistent_returns_false(self):
        """restoring a token that isn't archived returns False."""
        result = restore_token("no_such_archived_token", interactive=False)
        self.assertFalse(result)

    def test_restore_with_aliases(self):
        """restoring a token with aliases re-registers the aliases."""
        _import_and_forget(self.tmpdir, "restorable5", aliases=["rst5alias"])
        self.assertIsNone(get_token_by_alias("rst5alias"))

        restore_token("restorable5", interactive=False)
        self.assertIsNotNone(get_token_by_alias("rst5alias"))


class test_list_archived(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="cinnamonint_test_restore_list_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for name in ("listable1", "listable2"):
            _cleanup_token(name, "utility")
            _cleanup_archive(name)

    def test_list_shows_archived_tokens(self):
        """list_archived_tokens runs without error when archives exist."""
        _import_and_forget(self.tmpdir, "listable1")
        # just verify it doesn't raise
        list_archived_tokens()

    def test_list_empty_archive(self):
        """list_archived_tokens handles no archives gracefully."""
        # ensure archive dir is empty (or doesn't exist)
        list_archived_tokens()


if __name__ == "__main__":
    unittest.main()
