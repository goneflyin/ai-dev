"""
Tests for braindump.py — corresponds to features/braindump.feature
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import braindump


# ── Feature: write_braindump creates correct file ────────────────────────────


def test_write_braindump_creates_file(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(topic="Test Topic", body="Test body")
    assert Path(path).exists()


def test_write_braindump_creates_markdown_file(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(topic="Test Topic", body="Test body")
    assert path.endswith(".md")


def test_write_braindump_file_has_frontmatter(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(topic="Test Topic", body="Test body")
    content = Path(path).read_text()
    assert content.startswith("---")
    assert "topic: Test Topic" in content


def test_write_braindump_file_has_h1_heading(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(topic="Test Topic", body="Test body")
    content = Path(path).read_text()
    assert "# Test Topic" in content


def test_write_braindump_file_contains_body(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(topic="My Topic", body="My body text")
    content = Path(path).read_text()
    assert "My body text" in content


def test_write_braindump_with_tasks(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(
            topic="Topic", body="Body", tasks=["Task 1", "Task 2"]
        )
    content = Path(path).read_text()
    assert "- [ ] Task 1" in content
    assert "- [ ] Task 2" in content


def test_write_braindump_with_files(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(
            topic="Topic", body="Body", files=["/path/to/file.py"]
        )
    content = Path(path).read_text()
    assert "## Files Referenced" in content
    assert "`/path/to/file.py`" in content


def test_write_braindump_with_tags(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(
            topic="Topic", body="Body", tags=["python", "test"]
        )
    content = Path(path).read_text()
    assert "python" in content
    assert "test" in content


def test_write_braindump_default_tags_when_none(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        path = braindump.write_braindump(topic="Topic", body="Body")
    content = Path(path).read_text()
    assert "unsorted" in content


# ── Feature: last_braindump_age_hours ────────────────────────────────────────


def test_last_braindump_age_none_when_empty(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        age = braindump.last_braindump_age_hours()
    assert age is None


def test_last_braindump_age_small_for_recent_file(tmp_path):
    (tmp_path / "recent.md").write_text("content")
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        age = braindump.last_braindump_age_hours()
    assert age is not None
    assert age < 1


def test_last_braindump_age_large_for_old_file(tmp_path):
    old_file = tmp_path / "old.md"
    old_file.write_text("content")
    old_time = time.time() - 48 * 3600
    os.utime(old_file, (old_time, old_time))
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        age = braindump.last_braindump_age_hours()
    assert age is not None
    assert age > 24


def test_last_braindump_age_returns_float(tmp_path):
    (tmp_path / "note.md").write_text("content")
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        age = braindump.last_braindump_age_hours()
    assert isinstance(age, float)


# ── Feature: nudge_message ───────────────────────────────────────────────────


def test_nudge_message_when_no_files(tmp_path):
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        msg = braindump.nudge_message()
    assert msg is not None
    assert "/braindump" in msg


def test_nudge_message_is_none_when_recent(tmp_path):
    (tmp_path / "recent.md").write_text("content")
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        msg = braindump.nudge_message()
    assert msg is None


def test_nudge_message_present_when_overdue(tmp_path):
    old_file = tmp_path / "old.md"
    old_file.write_text("content")
    old_time = time.time() - 48 * 3600
    os.utime(old_file, (old_time, old_time))
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        msg = braindump.nudge_message()
    assert msg is not None


def test_nudge_message_mentions_hours_when_overdue(tmp_path):
    old_file = tmp_path / "old.md"
    old_file.write_text("content")
    old_time = time.time() - 48 * 3600
    os.utime(old_file, (old_time, old_time))
    with patch.object(braindump, "NOTES_DIR", tmp_path):
        msg = braindump.nudge_message()
    assert "48h" in msg
