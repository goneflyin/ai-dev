#!/usr/bin/env python3
"""
Braindump watchdog — checks if a braindump is overdue and outputs a nudge.

Designed for no_agent=True cron jobs: silent (exit 0) when no nudge is needed,
outputs a reminder message when one is.

Usage (cron schedule: daily):
    python3 ~/gbrain/braindump_watchdog.py

Output when nudge needed:
    📝 No session summary saved in 72h. `/braindump` to capture what you've been working on.
Output when recent enough:
    (silent — nothing printed)
"""

import sys
import os

# Add gbrain dir to path so we can import braindump
sys.path.insert(0, os.path.expanduser("~/gbrain"))
from braindump import nudge_message

if __name__ == "__main__":
    msg = nudge_message()
    if msg:
        print(msg)
        sys.exit(0)
    # Silent exit — no nudge needed
    sys.exit(0)