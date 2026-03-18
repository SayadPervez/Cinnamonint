"""
Test runner for learn mode — runs pytest and returns structured results.
"""

import subprocess
import sys
import os

from src.config.settings import PROJECT_ROOT


def run_full_test_suite():
    """run the full pytest suite. returns (passed, summary).

    passed: bool — True if all tests passed
    summary: str — human-readable output from pytest
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=120,
    )
    output = result.stdout + result.stderr
    passed = result.returncode == 0
    return passed, output


def run_specific_test(test_path):
    """run a specific test file. returns (passed, summary).

    test_path: relative path from project root (e.g., 'tests/math/test_plus.py')
    """
    abs_path = os.path.join(PROJECT_ROOT, test_path)
    if not os.path.exists(abs_path):
        return False, f"Test file not found: {test_path}"

    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=60,
    )
    output = result.stdout + result.stderr
    passed = result.returncode == 0
    return passed, output
