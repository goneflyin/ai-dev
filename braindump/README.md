# Braindump

Cross-session summarizer that writes structured records to `~/gbrain/notes/`. Used by Hermione (the Hermes agent) to persist a durable, human-readable account of what was discussed, decided, and built across multiple sessions.

## Files

| File | Purpose |
|---|---|
| `braindump.py` | Core library: writes markdown notes, checks if a nudge is needed |
| `braindump_watchdog.py` | CLI entry point for cron: outputs nudge message if overdue (no agent mode) |

## How It Works

When `/braindump` is invoked by the user:

1. Find the last braindump file's timestamp (excluding `idea-*` files)
2. `session_search` for sessions since that timestamp
3. `honcho_search` + `honcho_profile` for fact updates
4. Compose a structured cross-session summary
5. Save via `braindump.py`

The watchdog runs on a cron schedule and checks if a braindump is overdue (>24h).

## CLI Usage

```bash
# Write a braindump
python3 braindump.py --topic "May 11 work" --body "$(cat summary.md)" --session-id "abc123"

# Check if nudge is needed (for cron)
python3 braindump.py --nudge
```

## Installation

```bash
make install   # Copies both files to ~/gbrain/
```