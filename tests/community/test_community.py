"""
Test suite for the community exporter and importer.
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
    get_aliases,
    remove_token,
    token_exists,
)
from src.cinnamonint_logging.logger import init_db as init_logs
from src.seed import seed
from src.community.exporter import export_token, export_tokens
from src.community.importer import import_token, import_tokens_from_dir
from src.config.settings import PROJECT_ROOT, TESTS_DIR


def setUpModule():
    from src.config import settings
    settings.DB_DIR = os.path.join(settings.PROJECT_ROOT, "db")
    settings.REGISTRY_DB = os.path.join(settings.DB_DIR, "registry.db")
    settings.LOGS_DB = os.path.join(settings.DB_DIR, "logs.db")

    if not os.path.exists(settings.REGISTRY_DB):
        seed()


# ---------------------------------------------------------------------------
# helpers shared by tests
# ---------------------------------------------------------------------------

def _make_package(base_dir, name="testtoken", handler_code=None, test_file=None,
                  aliases=None, category="math", priority=1):
    """create a minimal cinnamonint token package directory."""
    pkg_dir = os.path.join(base_dir, name)
    os.makedirs(pkg_dir, exist_ok=True)

    if handler_code is None:
        # simple handler: removes its own keyword from the sentence
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
    """remove a test-imported token from DB, handler file, and test file."""
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


# ---------------------------------------------------------------------------
# export tests
# ---------------------------------------------------------------------------

class test_export(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="cinnamonint_test_export_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_export_existing_token(self):
        """exporting 'plus' produces a valid package directory."""
        result = export_token("plus", output_dir=self.tmpdir)
        self.assertIsNotNone(result)
        self.assertTrue(os.path.isdir(result))
        self.assertTrue(os.path.exists(os.path.join(result, "manifest.cinnamonint.json")))
        self.assertTrue(os.path.exists(os.path.join(result, "handler.cinnamonint.py")))
        self.assertTrue(os.path.exists(os.path.join(result, "test.cinnamonint.py")))

    def test_export_by_alias(self):
        """exporting by alias resolves to the canonical token name."""
        result = export_token("+", output_dir=self.tmpdir)
        self.assertIsNotNone(result)
        # directory name should be the canonical token name, not the alias
        self.assertEqual(os.path.basename(result), "plus")
        with open(os.path.join(result, "manifest.cinnamonint.json")) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["name"], "plus")

    def test_export_manifest_content(self):
        """exported manifest has correct metadata."""
        result = export_token("plus", output_dir=self.tmpdir)
        with open(os.path.join(result, "manifest.cinnamonint.json")) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["name"], "plus")
        self.assertEqual(manifest["category"], "math")
        self.assertEqual(manifest["priority"], 2)
        self.assertIn("+", manifest["aliases"])

    def test_export_handler_has_handle_function(self):
        """exported handler.cinnamonint.py contains a handle function."""
        result = export_token("plus", output_dir=self.tmpdir)
        with open(os.path.join(result, "handler.cinnamonint.py")) as f:
            source = f.read()
        self.assertIn("def handle(", source)

    def test_export_includes_test_file(self):
        """exported test.cinnamonint.py is a copy of the real test file."""
        result = export_token("plus", output_dir=self.tmpdir)
        test_file = os.path.join(result, "test.cinnamonint.py")
        self.assertTrue(os.path.exists(test_file))
        with open(test_file) as f:
            content = f.read()
        self.assertIn("def test_", content)

    def test_export_nonexistent_token(self):
        """exporting a non-existent token returns None."""
        result = export_token("nonexistent_xyz_token", output_dir=self.tmpdir)
        self.assertIsNone(result)

    def test_export_multiple_tokens(self):
        """export_tokens creates a subfolder for each token."""
        results = export_tokens(["plus", "minus"], output_dir=self.tmpdir)
        self.assertEqual(len(results), 2)
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, "plus")))
        self.assertTrue(os.path.isdir(os.path.join(self.tmpdir, "minus")))


# ---------------------------------------------------------------------------
# import tests
# ---------------------------------------------------------------------------

class test_import(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="cinnamonint_test_import_")
        self.imported_tokens = []  # (name, category) pairs for teardown

    def tearDown(self):
        for name, category in self.imported_tokens:
            _cleanup_token(name, category)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_import_valid_package(self):
        """importing a valid package registers the token."""
        pkg = _make_package(self.tmpdir, name="testtoken_import")
        self.imported_tokens.append(("testtoken_import", "math"))

        result = import_token(pkg, interactive=False)
        self.assertTrue(result)
        self.assertTrue(token_exists("testtoken_import"))

    def test_import_creates_handler_file(self):
        """importing copies the handler to tokens/<category>/<name>.py."""
        pkg = _make_package(self.tmpdir, name="testtoken_file", category="math")
        self.imported_tokens.append(("testtoken_file", "math"))

        import_token(pkg, interactive=False)
        token = get_token("testtoken_file")
        self.assertIsNotNone(token)

        handler_abs = os.path.join(PROJECT_ROOT, token["handler_path"])
        self.assertTrue(os.path.exists(handler_abs))
        # path should follow tokens/<category>/<name>.py convention
        self.assertTrue(token["handler_path"].endswith("testtoken_file.py"))

    def test_import_creates_test_file(self):
        """importing with a test file copies it to tests/<category>/."""
        test_content = (
            'import unittest\n'
            'import sys, os\n'
            'sys.path.insert(0, os.path.dirname(os.path.dirname(\n'
            '    os.path.dirname(os.path.abspath(__file__)))))\n'
            'from tokens.math.testtoken_tf import handle\n\n'
            'class test_testtoken_tf(unittest.TestCase):\n'
            '    def test_001(self):\n'
            '        self.assertEqual(handle("hello testtoken_tf world"), "hello  world")\n\n'
            'if __name__ == "__main__":\n'
            '    unittest.main()\n'
        )
        pkg = _make_package(self.tmpdir, name="testtoken_tf",
                            category="math", test_file=test_content)
        self.imported_tokens.append(("testtoken_tf", "math"))

        import_token(pkg, interactive=False)

        test_file = os.path.join(TESTS_DIR, "math", "test_testtoken_tf.py")
        self.assertTrue(os.path.exists(test_file))

        with open(test_file) as f:
            content = f.read()
        self.assertIn("def test_001(self):", content)

    def test_import_duplicate_name_blocked(self):
        """importing a token whose name already exists is blocked."""
        result = import_token(
            _make_package(self.tmpdir, name="plus"),
            interactive=False,
        )
        self.assertFalse(result)

    def test_import_alias_conflict_blocked(self):
        """importing a token whose alias conflicts with an existing token is blocked."""
        # '+' is an alias of 'plus' — must be blocked
        result = import_token(
            _make_package(self.tmpdir, name="newtok", aliases=["+"]),
            interactive=False,
        )
        self.assertFalse(result)

    def test_import_missing_manifest(self):
        """importing from a directory without manifest.cinnamonint.json fails."""
        empty_dir = os.path.join(self.tmpdir, "empty")
        os.makedirs(empty_dir)
        result = import_token(empty_dir, interactive=False)
        self.assertFalse(result)

    def test_import_with_failing_tests_rolls_back(self):
        """failing tests abort import and remove any written files."""
        test_content = (
            'import unittest\n'
            'import sys, os\n'
            'sys.path.insert(0, os.path.dirname(os.path.dirname(\n'
            '    os.path.dirname(os.path.abspath(__file__)))))\n'
            'from tokens.math.testtoken_fail import handle\n\n'
            'class test_testtoken_fail(unittest.TestCase):\n'
            '    def test_001(self):\n'
            '        self.assertEqual(handle("hello testtoken_fail"), "WRONG")\n\n'
            'if __name__ == "__main__":\n'
            '    unittest.main()\n'
        )
        pkg = _make_package(self.tmpdir, name="testtoken_fail", test_file=test_content)

        result = import_token(pkg, interactive=False)
        self.assertFalse(result)
        # token must not be in DB
        self.assertFalse(token_exists("testtoken_fail"))

    def test_import_no_test_cases(self):
        """importing without a tests file still works."""
        pkg = _make_package(self.tmpdir, name="testtoken_notest")
        self.imported_tokens.append(("testtoken_notest", "math"))

        result = import_token(pkg, interactive=False)
        self.assertTrue(result)

    def test_import_stores_test_path_in_db(self):
        """imported tokens with test files have test_path set in DB."""
        test_content = (
            'import unittest\n'
            'import sys, os\n'
            'sys.path.insert(0, os.path.dirname(os.path.dirname(\n'
            '    os.path.dirname(os.path.abspath(__file__)))))\n'
            'from tokens.math.testtoken_nodb import handle\n\n'
            'class test_testtoken_nodb(unittest.TestCase):\n'
            '    def test_001(self):\n'
            '        self.assertEqual(handle("x testtoken_nodb y"), "x  y")\n\n'
            'if __name__ == "__main__":\n'
            '    unittest.main()\n'
        )
        pkg = _make_package(self.tmpdir, name="testtoken_nodb",
                            category="math", test_file=test_content)
        self.imported_tokens.append(("testtoken_nodb", "math"))

        import_token(pkg, interactive=False)
        token = get_token("testtoken_nodb")
        self.assertIsNotNone(token["test_path"])
        self.assertTrue(token["test_path"].endswith("test_testtoken_nodb.py"))


# ---------------------------------------------------------------------------
# bulk import tests
# ---------------------------------------------------------------------------

class test_bulk_import(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="cinnamonint_test_bulk_")
        self.imported_tokens = []

    def tearDown(self):
        for name, category in self.imported_tokens:
            _cleanup_token(name, category)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_import_dir_scans_subfolders(self):
        """import_tokens_from_dir imports all valid packages in subfolders."""
        _make_package(self.tmpdir, name="bulktoken_a", category="math")
        _make_package(self.tmpdir, name="bulktoken_b", category="math")
        self.imported_tokens += [("bulktoken_a", "math"), ("bulktoken_b", "math")]

        results = import_tokens_from_dir(self.tmpdir, interactive=False)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(ok for _, ok in results))

    def test_import_dir_skips_non_packages(self):
        """subfolders without manifest.cinnamonint.json are ignored."""
        _make_package(self.tmpdir, name="bulktoken_c", category="math")
        self.imported_tokens.append(("bulktoken_c", "math"))

        # create a plain non-package dir
        os.makedirs(os.path.join(self.tmpdir, "not_a_package"))

        results = import_tokens_from_dir(self.tmpdir, interactive=False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "bulktoken_c")

    def test_import_dir_empty(self):
        """parent dir with no packages returns empty list."""
        results = import_tokens_from_dir(self.tmpdir, interactive=False)
        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# roundtrip test
# ---------------------------------------------------------------------------

class test_export_import_roundtrip(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="cinnamonint_test_roundtrip_")
        self.imported_token = None

    def tearDown(self):
        if self.imported_token:
            name, category = self.imported_token
            _cleanup_token(name, category)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_roundtrip(self):
        """export plus, rename manifest name, import — works end to end."""
        export_dir = os.path.join(self.tmpdir, "export")
        pkg_path = export_token("plus", output_dir=export_dir)
        self.assertIsNotNone(pkg_path)

        # update manifest name to avoid conflict with existing 'plus'
        manifest_path = os.path.join(pkg_path, "manifest.cinnamonint.json")
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest["name"] = "plus_copy"
        manifest["aliases"] = ["plus_copy_alias"]
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        # also rename the package directory to match
        new_pkg_path = os.path.join(export_dir, "plus_copy")
        os.rename(pkg_path, new_pkg_path)

        self.imported_token = ("plus_copy", "math")
        result = import_token(new_pkg_path, interactive=False)
        self.assertTrue(result)

        token = get_token("plus_copy")
        self.assertIsNotNone(token)
        self.assertEqual(token["category"], "math")


if __name__ == "__main__":
    unittest.main()