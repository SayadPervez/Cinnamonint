"""
pytest configuration — ensure project root is on sys.path for all tests.
"""

import sys
import os

# add project root so all test files can import src.*, tokens.*, etc.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
