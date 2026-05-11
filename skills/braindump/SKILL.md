---
name: braindump
description: "File a cross-session summary to gbrain (~/gbrain/notes/). Usage: /braindump [topic] — gathers sessions since the last dump, then writes a structured record of decisions, files, tasks, and follow-ups."
---

# Braindump — Cross-Session Summary to gbrain

When the user says `/braindump` (optionally with a topic), do the following:

## Steps

1. **Find the last braindump timestamp.**
   List files in `~/gbrain/notes/` (top-level only, not `ideas/` subdirectory). Find the most recently modified `*.md` file excluding any `idea-*` files. Use its mtime as the cutoff. If no prior braindump exists, use 7 days ago as the cutoff.

2. **Gather sessions since that timestamp.**
   Call `session_search` with a broad query to retrieve sessions that occurred after the cutoff timestamp.

3. **Pull fact updates from Honcho.**
   Call `honcho_search` for any facts relevant to recent work. Call `honcho_profile` to check for updated peer cards or preference corrections learned since the last dump.

4. **Compose a structured cross-session summary.**
   The body should be a markdown document covering all sessions since the last dump, organized by topic or session:
   - **Decisions made** — architectural choices, approach changes, things Scott said to do differently
   - **Files created or modified** — absolute paths, what changed and why
   - **Tasks** — Todoist tasks created or queued, with IDs if known
   - **Follow-ups and next actions** — unfinished work, things to pick up next session
   - **Preferences and corrections** — anything Scott corrected about how Hermione should work

   Keep each section concise but specific — the point is to have exact paths, IDs, and decisions recoverable without re-reading session transcripts.

5. **Save the braindump.**
   Run the braindump script with the composed body:
   ```bash
   python3 ~/gbrain/braindump.py --topic "<topic>" --body "<summary markdown>" [--files '["file1","file2"]'] [--tasks '["task1","task2"]'] [--tags "tag1,tag2"] [--session-id "<id>"]
   ```
   The script returns JSON: `{"ok": true, "path": "/path/to/file.md"}`

6. **Confirm to the user** that the braindump landed, mentioning the path.

## What to capture

- Decisions and rationale (not just "we changed X" but "we changed X because Y")
- Absolute file paths for anything created or significantly modified
- Todoist task IDs or titles for anything queued
- Explicit follow-ups Scott mentioned ("remind me to...", "next time we should...")
- Any preference or behavior corrections Scott made during the sessions

## Notes

- Brainstorm idea notes from the dashboard live in `~/gbrain/notes/ideas/` — do not confuse these with braindumps.
- If the topic is not provided by the user, infer it from the sessions gathered (e.g. "Multi-session: May 8–10 — auth refactor, goal system").
- This is Hermione's reference — Scott will not read these files directly. Write for future-Hermione who needs to give Scott a detailed status update.
