"""
Test setup for learn mode — creates a test registry with the new token registered.

Usage:
    python -m src.learn.test_setup <word>
    python -m src.learn.test_setup <word> --clean

This tool:
  1. Copies the production registry.db → test_registry.db
  2. Parses METADATA from the new handler file
  3. Registers the new token in test_registry.db

After this, tests can be run against the test registry:
    CINNAMONINT_TEST_DB=1 python -m pytest tests/

The --clean flag removes test_registry.db.
"""

import sys
import os
import shutil

# ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config.settings import PROJECT_ROOT, REGISTRY_DB, TEST_REGISTRY_DB, TOKENS_DIR
from src.learn.learner import _find_and_validate_handler, _parse_metadata


def _copy_production_db():
    """copy production registry to test registry."""
    if not os.path.exists(REGISTRY_DB):
        print(f"Error: production registry not found at {REGISTRY_DB}")
        sys.exit(1)
    shutil.copy2(REGISTRY_DB, TEST_REGISTRY_DB)
    print(f"Copied registry.db → test_registry.db")


def _register_token_in_test_db(word):
    """register the new token in the test registry."""
    # set env var so store.py connects to test DB
    os.environ["CINNAMONINT_TEST_DB"] = "1"

    from src.registry.store import add_token

    # find the handler file
    handler_filename = f"{word}.py"
    handler_path = None

    for category_dir in os.listdir(TOKENS_DIR):
        cat_path = os.path.join(TOKENS_DIR, category_dir)
        if not os.path.isdir(cat_path):
            continue
        candidate = os.path.join(cat_path, handler_filename)
        if os.path.exists(candidate):
            handler_path = os.path.join("tokens", category_dir, handler_filename)
            break

    if handler_path is None:
        print(f"Error: handler file not found: tokens/<category>/{word}.py")
        sys.exit(1)

    # parse METADATA
    abs_path = os.path.join(PROJECT_ROOT, handler_path)
    metadata = _parse_metadata(abs_path)
    if metadata is None:
        print("Error: METADATA constant not found or malformed in handler file.")
        sys.exit(1)

    # determine test path
    category = metadata["category"]
    test_path = os.path.join("tests", category, f"test_{word}.py")

    # register
    try:
        add_token(
            name=metadata["name"],
            category=metadata["category"],
            priority=metadata["priority"],
            handler_path=handler_path,
            aliases=metadata["aliases"] if metadata["aliases"] else None,
            destructive=metadata["destructive"],
            downloads=metadata["downloads"],
            uploads=metadata["uploads"],
            author="local",
            source="learn",
            version="1.0.0",
            test_path=test_path,
        )
        print(f"Registered '{word}' in test_registry.db")
        print(f"  category: {metadata['category']}")
        print(f"  priority: {metadata['priority']}")
        print(f"  aliases:  {metadata['aliases']}")
        print(f"  handler:  {handler_path}")
    except Exception as e:
        print(f"Error registering token: {e}")
        sys.exit(1)


def _clean():
    """remove the test registry."""
    if os.path.exists(TEST_REGISTRY_DB):
        os.remove(TEST_REGISTRY_DB)
        print("Removed test_registry.db")
    else:
        print("test_registry.db does not exist — nothing to clean.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.learn.test_setup <word> [--clean]")
        sys.exit(1)

    word = sys.argv[1].strip().lower()

    if word == "--clean" or (len(sys.argv) > 2 and "--clean" in sys.argv):
        _clean()
        if word == "--clean":
            return
        # if both word and --clean provided, clean and exit
        if "--clean" in sys.argv[2:]:
            _clean()
            return

    _copy_production_db()
    _register_token_in_test_db(word)

    print(f"\nReady. Run tests with:")
    print(f"  CINNAMONINT_TEST_DB=1 python -m pytest tests/")
    print(f"\nClean up with:")
    print(f"  python -m src.learn.test_setup --clean")


if __name__ == "__main__":
    main()
