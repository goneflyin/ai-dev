"""
Import smoke tests for gbrain modules — corresponds to features/imports.feature
"""

import sys
import importlib
from pathlib import Path

import pytest

GBRAIN_DIR = str(Path(__file__).parent.parent)
if GBRAIN_DIR not in sys.path:
    sys.path.insert(0, GBRAIN_DIR)


def test_todoist_helper_imports():
    mod = importlib.import_module("todoist_helper")
    assert mod is not None


def test_review_matter_imports():
    mod = importlib.import_module("review_matter")
    assert mod is not None


def test_status_collect_imports():
    mod = importlib.import_module("status_collect")
    assert mod is not None


def test_sync_matter_imports():
    pytest.importorskip("requests", reason="requests not installed — skipping sync_matter import test")
    mod = importlib.import_module("sync_matter")
    assert mod is not None
