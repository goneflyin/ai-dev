#!/usr/bin/env python3
"""
Status Collector — gathers all in-flight state for the "what's up?" executive summary.
Outputs JSON to stdout. Designed to be run by the Hermes agent for check-ins.

Usage:
    python3 ~/gbrain/status_collect.py
    python3 ~/gbrain/status_collect.py --detailed   # show article titles too
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

GBRAIN_DIR = Path.home() / "gbrain"
ARTICLES_DIR = GBRAIN_DIR / "articles"
NOTES_DIR = GBRAIN_DIR / "notes"
SESSION_DIR = Path.home() / ".hermes" / "sessions"
SKILLS_DIR = Path.home() / ".hermes" / "skills"
TODOIST_HELPER = GBRAIN_DIR / "todoist_helper.py"


def collect_articles_state():
    """Gather captures/gBrain article stats."""
    result = {
        "total": 0,
        "annotated": 0,
        "unannotated": 0,
        "recent_24h": 0,
        "recent_3": [],
    }

    annotations_file = GBRAIN_DIR / "annotations.jsonl"
    annotated_ids = set()
    if annotations_file.exists():
        with open(annotations_file) as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    aid = rec.get("article_id")
                    if aid:
                        annotated_ids.add(aid)
                except json.JSONDecodeError:
                    pass

    md_files = sorted(
        ARTICLES_DIR.rglob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    now = datetime.now().timestamp()
    for md in md_files:
        result["total"] += 1
        # Check if annotated by looking for matter_id
        content = md.read_text(encoding="utf-8", errors="replace")
        matter_id = ""
        for line in content.split("\n"):
            if line.startswith("matter_id:"):
                matter_id = line.split(":", 1)[1].strip()
                break

        is_annotated = matter_id in annotated_ids
        if is_annotated:
            result["annotated"] += 1
        else:
            result["unannotated"] += 1

        # Check recency
        age_hours = (now - md.stat().st_mtime) / 3600
        if age_hours < 24:
            result["recent_24h"] += 1

        # Collect top 3 recent for highlights
        if len(result["recent_3"]) < 3:
            title = ""
            for line in content.split("\n"):
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip("'\"")
                    break
            if not title:
                for line in content.split("\n"):
                    if line.startswith("# ") and not line.startswith("## "):
                        title = line[2:].strip()
                        break
            source = ""
            for line in content.split("\n"):
                if line.startswith("source:"):
                    source = line.split(":", 1)[1].strip().strip("'\"")
                    break

            saved = ""
            for line in content.split("\n"):
                if line.startswith("date_saved:"):
                    saved = line.split(":", 1)[1].strip()[:10]
                    break
            if not saved:
                for line in content.split("\n"):
                    if line.startswith("date_synced:"):
                        saved = line.split(":", 1)[1].strip()[:10]
                        break
            result["recent_3"].append({
                "title": title or "Untitled",
                "source": source,
                "saved": saved,
                "age_hours": round(age_hours, 1),
                "is_annotated": is_annotated,
            })

    return result


def collect_braindump_state():
    """Gather braindump/notes state."""
    result = {
        "total_notes": 0,
        "last_note_path": None,
        "last_note_age_hours": None,
        "last_note_topic": None,
    }

    md_files = sorted(
        NOTES_DIR.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    result["total_notes"] = len(md_files)

    if md_files:
        latest = md_files[0]
        now = datetime.now().timestamp()
        age_hours = (now - latest.stat().st_mtime) / 3600
        result["last_note_path"] = str(latest.name)
        result["last_note_age_hours"] = round(age_hours, 1)

        # Extract topic from YAML frontmatter
        content = latest.read_text(encoding="utf-8", errors="replace")
        for line in content.split("\n"):
            if line.startswith("topic:"):
                result["last_note_topic"] = line.split(":", 1)[1].strip()
                break

    return result


def collect_cron_state():
    """Read cron job state from Hermes sessions directory."""
    result = {
        "jobs": [],
        "recent_failures": [],
    }

    # Read from cron state file if it exists
    cron_state = Path.home() / ".hermes" / "cron" / "state.json"
    if cron_state.exists():
        try:
            state = json.loads(cron_state.read_text())
            for job_id, job in state.items():
                entry = {
                    "job_id": job_id,
                    "name": job.get("name", ""),
                    "schedule": job.get("schedule", ""),
                    "enabled": job.get("enabled", False),
                    "last_run_at": job.get("last_run_at", ""),
                    "last_status": job.get("last_status", ""),
                }
                result["jobs"].append(entry)
                if job.get("last_status") == "error":
                    result["recent_failures"].append(job_id)
        except (json.JSONDecodeError, Exception):
            pass

    return result


def collect_recent_sessions(limit=3):
    """Get info on recent Hermes sessions."""
    result = {
        "sessions": [],
    }

    if not SESSION_DIR.exists():
        return result

    sessions = sorted(
        SESSION_DIR.glob("session_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for s in sessions[:limit]:
        try:
            data = json.loads(s.read_text())
            title = data.get("title") or ""
            platform = data.get("platform", "")
            started = data.get("session_start", "")
            msg_count = data.get("message_count", 0)
            result["sessions"].append({
                "id": data.get("session_id", s.stem),
                "title": title[:80] if title else "",
                "platform": platform,
                "started": started,
                "message_count": msg_count,
            })
        except (json.JSONDecodeError, Exception):
            pass

    return result


def collect_todoist_state():
    """Check if Todoist has any pending tasks (via helper if available)."""
    result = {
        "available": False,
        "pending_count": None,
        "flagged_count": None,
    }

    if TODOIST_HELPER.exists():
        result["available"] = True
        try:
            sys.path.insert(0, str(GBRAIN_DIR))
            # We don't import here — too heavy for a quick collect.
            # Check if token is configured
            from todoist_helper import TOKEN
            result["configured"] = bool(TOKEN)
        except ImportError:
            result["configured"] = False
    else:
        result["configured"] = False

    return result


def main(detailed=False):
    now = datetime.now(timezone.utc)

    report = {
        "timestamp": now.isoformat(),
        "articles": collect_articles_state(),
        "braindump": collect_braindump_state(),
        "cron": collect_cron_state(),
        "sessions": collect_recent_sessions(limit=3),
        "todoist": collect_todoist_state(),
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    detailed = "--detailed" in sys.argv
    main(detailed=detailed)