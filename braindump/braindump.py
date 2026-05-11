#!/usr/bin/env python3
"""
Braindump — writes session summaries to gbrain notes.
Usage:
    python3 ~/gbrain/braindump.py --topic "<topic>" --body "<markdown>" [--files '[...]'] [--tasks '[...]'] [--tags "..."] [--session-id "..."]
    python3 ~/gbrain/braindump.py --nudge   # Check if nudge is needed (outputs JSON)
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

NOTES_DIR = Path.home() / "gbrain" / "notes"


def slugify(text):
    """Convert text to a filesystem-safe slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug[:60].rstrip('-')


def write_braindump(topic, body, session_id=None, tasks=None, files=None, tags=None):
    """Write a structured braindump note to ~/gbrain/notes/."""
    now = datetime.now()
    slug = slugify(topic)
    fname = f"{now.strftime('%Y%m%d_%H%M')}-{slug}.md"
    note_path = NOTES_DIR / fname

    tags_str = ", ".join(tags) if tags else "unsorted"

    lines = [
        "---",
        f"date: {now.strftime('%Y-%m-%d')}",
        f"time: {now.strftime('%H:%M')}",
        f"topic: {topic}",
        f"tags: {tags_str}",
    ]
    if session_id:
        lines.append(f"hermes_session: {session_id}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {topic}")
    lines.append("")

    if body:
        lines.append(body)
        lines.append("")

    if files:
        lines.append("## Files Referenced")
        lines.append("")
        for f in files:
            lines.append(f"- `{f}`")
        lines.append("")

    if tasks:
        lines.append("## Tasks Created")
        lines.append("")
        for t in tasks:
            lines.append(f"- [ ] {t}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Braindump auto-generated on {now.strftime('%Y-%m-%d at %H:%M')}*")
    lines.append("")

    content = "\n".join(lines)
    note_path.write_text(content, encoding="utf-8")
    return str(note_path)


def last_braindump_age_hours() -> Optional[float]:
    """Return hours since the most recent braindump file, or None if none exist."""
    md_files = sorted(NOTES_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not md_files:
        return None
    now = datetime.now().timestamp()
    age_seconds = now - md_files[0].stat().st_mtime
    return age_seconds / 3600


def nudge_message() -> Optional[str]:
    """Return a Telegram nudge message if one is needed, or None."""
    age = last_braindump_age_hours()
    if age is None:
        return "📝 No session summary saved yet. `/braindump` to capture what you've been working on."
    if age > 24:
        hours = int(age)
        return f"📝 No session summary saved in {hours}h. `/braindump` to capture what you've been working on."
    return None  # recent enough


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Write a gbrain braindump note")
    parser.add_argument("--topic", required=True, help="Session topic")
    parser.add_argument("--body", required=True, help="Markdown body text")
    parser.add_argument("--session-id", help="Hermes session ID")
    parser.add_argument("--tasks", help='JSON array of task strings')
    parser.add_argument("--files", help='JSON array of file paths')
    parser.add_argument("--tags", help='Comma-separated tags')
    parser.add_argument("--nudge", action="store_true", help="Check if nudge is needed (outputs JSON)")

    args = parser.parse_args()

    if args.nudge:
        msg = nudge_message()
        if msg:
            print(json.dumps({"nudge": True, "message": msg}))
        else:
            print(json.dumps({"nudge": False}))
        sys.exit(0)

    tasks = json.loads(args.tasks) if args.tasks else None
    files = json.loads(args.files) if args.files else None
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    path = write_braindump(
        topic=args.topic,
        body=args.body,
        session_id=args.session_id,
        tasks=tasks,
        files=files,
        tags=tags,
    )
    print(json.dumps({"ok": True, "path": path}))