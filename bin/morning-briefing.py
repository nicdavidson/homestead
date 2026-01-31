#!/usr/bin/env python3
"""Fetch RSS news feeds and post a morning briefing to the outbox.

Designed to be called by Almanac as a command-type job.
"""
import sys
from pathlib import Path

# Add common package to path
common_path = str(Path(__file__).resolve().parent.parent / "packages" / "common")
if common_path not in sys.path:
    sys.path.insert(0, common_path)

from common.news import get_briefing
from common.outbox import post_message

CHAT_ID = 6038780843
OUTBOX_DB = Path("~/.homestead/outbox.db").expanduser()


def main() -> None:
    briefing = get_briefing()
    post_message(
        db_path=str(OUTBOX_DB),
        chat_id=CHAT_ID,
        agent_name="Almanac",
        message=briefing,
    )
    print(f"Morning briefing posted to outbox ({len(briefing)} chars)")


if __name__ == "__main__":
    main()
