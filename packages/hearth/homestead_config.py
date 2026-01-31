"""Homestead-specific configuration for hearth.

All values can be overridden via environment variables.
"""

import os
from pathlib import Path

HOMESTEAD_DATA_DIR = os.environ.get("HOMESTEAD_DATA_DIR", "~/.homestead")

LORE_DIR = os.environ.get(
    "LORE_DIR",
    str(Path(__file__).resolve().parent.parent.parent / "lore"),
)

DEFAULT_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))
