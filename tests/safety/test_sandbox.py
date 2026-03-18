"""
Test suite for the sandbox — static analysis of handler source code.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.safety.sandbox import analyze_handler_code, auto_detect_flags, has_extract_operands


class test_sandbox_detection(unittest.TestCase):
    """test that suspicious patterns are correctly detected."""

    def test_clean_handler(self):
        """a clean math handler produces no findings."""
        code = '''
import re

def handle(sentence):
    return sentence.replace("hello", "world")
'''
        findings = analyze_handler_code(code)
        self.assertEqual(len(findings), 0)

    def test_os_system(self):
        """os.system() is flagged as high severity."""
        code = '''
import os

def handle(sentence):
    os.system("ls")
    return sentence
'''
        findings = analyze_handler_code(code)
        patterns = [f["pattern"] for f in findings]
        self.assertIn("os.system()", patterns)
        severity = next(f["severity"] for f in findings if f["pattern"] == "os.system()")
        self.assertEqual(severity, "high")

    def test_subprocess_shell_true(self):
        """subprocess with shell=True is flagged."""
        code = '''
import subprocess

def handle(sentence):
    subprocess.call("ls", shell=True)
    return sentence
'''
        findings = analyze_handler_code(code)
        patterns = [f["pattern"] for f in findings]
        # should find both "import subprocess" and "shell=True"
        has_shell = any("shell=True" in p for p in patterns)
        self.assertTrue(has_shell)

    def test_eval(self):
        """bare eval() is flagged."""
        code = '''
def handle(sentence):
    return eval(sentence)
'''
        findings = analyze_handler_code(code)
        patterns = [f["pattern"] for f in findings]
        self.assertIn("eval()", patterns)

    def test_exec(self):
        """bare exec() is flagged."""
        code = '''
def handle(sentence):
    exec("x = 1")
    return sentence
'''
        findings = analyze_handler_code(code)
        patterns = [f["pattern"] for f in findings]
        self.assertIn("exec()", patterns)

    def test_file_deletion(self):
        """os.remove is flagged."""
        code = '''
import os

def handle(sentence):
    os.remove("/tmp/test")
    return sentence
'''
        findings = analyze_handler_code(code)
        patterns = [f["pattern"] for f in findings]
        self.assertIn("os.remove()", patterns)

    def test_shutil_rmtree(self):
        """shutil.rmtree is flagged."""
        code = '''
import shutil

def handle(sentence):
    shutil.rmtree("/tmp/test")
    return sentence
'''
        findings = analyze_handler_code(code)
        patterns = [f["pattern"] for f in findings]
        self.assertIn("shutil.rmtree()", patterns)

    def test_network_call(self):
        """urllib usage is flagged."""
        code = '''
import urllib.request

def handle(sentence):
    urllib.request.urlopen("http://example.com")
    return sentence
'''
        findings = analyze_handler_code(code)
        has_network = any("urllib" in f["pattern"] or "network" in f["description"].lower()
                          for f in findings)
        self.assertTrue(has_network)

    def test_environ_access(self):
        """os.environ attribute access is flagged."""
        code = '''
import os

def handle(sentence):
    key = os.environ["SECRET"]
    return sentence
'''
        findings = analyze_handler_code(code)
        patterns = [f["pattern"] for f in findings]
        self.assertIn("os.environ", patterns)

    def test_destructive_string_pattern(self):
        """strings containing 'rm -rf' are flagged."""
        code = '''
import os

def handle(sentence):
    os.system("rm -rf /tmp/test")
    return sentence
'''
        findings = analyze_handler_code(code)
        has_rm = any("rm -rf" in f.get("pattern", "") for f in findings)
        self.assertTrue(has_rm)

    def test_syntax_error(self):
        """code with syntax errors produces a SyntaxError finding."""
        code = "def handle(sentence)\n    return sentence"
        findings = analyze_handler_code(code)
        self.assertTrue(any(f["pattern"] == "SyntaxError" for f in findings))


class test_sandbox_auto_flags(unittest.TestCase):
    """test auto_detect_flags for token flag suggestion."""

    def test_clean_code_no_flags(self):
        """clean code suggests no flags."""
        code = '''
def handle(sentence):
    return sentence.upper()
'''
        flags = auto_detect_flags(code)
        self.assertFalse(flags["destructive"])
        self.assertFalse(flags["downloads"])
        self.assertFalse(flags["uploads"])

    def test_destructive_flag_detected(self):
        """code with file deletion suggests destructive flag."""
        code = '''
import os

def handle(sentence):
    os.remove("/tmp/test")
    return sentence
'''
        flags = auto_detect_flags(code)
        self.assertTrue(flags["destructive"])

    def test_network_flag_detected(self):
        """code with network calls suggests downloads flag."""
        code = '''
import urllib.request

def handle(sentence):
    urllib.request.urlopen("http://example.com")
    return sentence
'''
        flags = auto_detect_flags(code)
        self.assertTrue(flags["downloads"])


class test_sandbox_extract_operands(unittest.TestCase):
    """test has_extract_operands detection."""

    def test_handler_with_extract_operands(self):
        """handler defining extract_operands is detected."""
        code = '''
def handle(sentence):
    return sentence

def extract_operands(sentence):
    return ("upload", "/images/trip", "drive")
'''
        self.assertTrue(has_extract_operands(code))

    def test_handler_without_extract_operands(self):
        """handler without extract_operands returns False."""
        code = '''
def handle(sentence):
    return sentence
'''
        self.assertFalse(has_extract_operands(code))

    def test_syntax_error_returns_false(self):
        """unparseable code returns False."""
        code = "def handle(sentence)\n    return sentence"
        self.assertFalse(has_extract_operands(code))


if __name__ == "__main__":
    unittest.main()
