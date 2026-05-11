# ai-dev

Tools and system extensions built by delegation from Hermes. This is the development workspace — code is written, tested, and verified here, then installed to target locations via `make install`.

## Repository Structure

```
ai-dev/
├── AGENTS.md                          # Coding standards for AI agents (Claude Code, Codex)
├── README.md                          # This file
├── review-dashboard/                  # gBrain Review Dashboard
│   ├── review_server.py               #   Web server: article review UI
│   ├── SPEC.md                        #   Architecture spec
│   └── REVIEW.md                      #   Codex security review findings
├── braindump/                         # Cross-session summarizer
│   ├── braindump.py                   #   Core library: write notes, check nudge timing
│   └── braindump_watchdog.py          #   Cron entry point for nudge
├── gbrain/                            # Read-later sync & pipeline utilities
│   ├── sync_matter.py                 #   Matter API sync to local markdown
│   ├── todoist_helper.py              #   Todoist task management
│   ├── review_matter.py              #   Interactive review sessions
│   └── status_collect.py              #   System status for check-ins
└── skills/                            # Hermes agent skills
    ├── README.md                      #   Skills documentation
    └── braindump/
        └── SKILL.md                   #   Braindump skill definition
```

## Installation

Each project has a `Makefile` with an `install` target that copies files to their target locations:

```bash
# Install everything
cd review-dashboard && make install
cd ../braindump && make install
cd ../gbrain && make install
cd ../skills && make install
```

Target locations:
- `review-dashboard/` → `~/gbrain/review_server.py`
- `braindump/` → `~/gbrain/braindump.py`, `~/gbrain/braindump_watchdog.py`
- `gbrain/` → `~/gbrain/*.py`
- `skills/` → `~/.hermes/skills/*/`

## Development Workflow

All coding is delegated to Claude Code (or another agent harness). The agent:

1. Works in this repository
2. Follows the guidelines in `AGENTS.md`
3. Writes Gherkin specs and tests
4. Verifies changes before concluding
5. Installs with `make install` when done