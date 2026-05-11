# gbrain — Read-Later Sync & Pipeline Utilities

Utility scripts that support the gbrain knowledge management system. These sync articles from Matter, perform review sessions, manage Todoist tasks, and collect status summaries.

## Files

| File | Purpose |
|---|---|
| `sync_matter.py` | Syncs Matter articles to local markdown files at ~/gbrain/articles/ |
| `todoist_helper.py` | Todoist API helper for creating tasks, querying projects |
| `review_matter.py` | Interactive CLI review session for Matter articles |
| `status_collect.py` | Collects system status for executive check-ins |

## Dependencies

- `sync_matter.py` requires the Matter API (token in `~/.hermes/.env`)
- `todoist_helper.py` requires Todoist API (token in `~/.hermes/.env`)
- All scripts expect the gbrain directory structure at `~/gbrain/`

## Installation

```bash
make install   # Copies all scripts to ~/gbrain/
```