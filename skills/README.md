# Skills — Hermes Agent Skills

Hermes agent skills define how Hermione behaves when triggered by commands or keywords. Each skill is a `SKILL.md` file loaded into context.

## Directories

| Directory | Skill | Trigger |
|---|---|---|
| `braindump/` | Braindump | `/braindump [topic]` |

### braindump

When the user types `/braindump`, Hermione:

1. Finds the last braindump timestamp
2. Calls `session_search` for sessions since that cutoff
3. Calls `honcho_search` and `honcho_profile` for fact updates
4. Composes a structured cross-session summary (decisions, files, tasks, follow-ups)
5. Saves via `braindump.py`

This is Hermione's durable external memory — written for future-Hermione to retrieve when Scott asks about past work.

## Installation

```bash
make install   # Copies skills to ~/.hermes/skills/
```