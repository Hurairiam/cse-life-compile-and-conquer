"""
tests/conftest.py
Puts the project root on sys.path so `pytest` works from anywhere
without an installed package or a PYTHONPATH dance.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
