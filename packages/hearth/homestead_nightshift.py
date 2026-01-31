"""Nightshift daemon with homestead integration.

Run as::

    python -m packages.hearth.homestead_nightshift

Or directly::

    python packages/hearth/homestead_nightshift.py
"""

import asyncio
import logging
import time
from pathlib import Path

from homestead_config import HOMESTEAD_DATA_DIR, LORE_DIR, DEFAULT_CHAT_ID
from homestead_integration import (
    setup_watchtower,
    send_to_telegram,
    read_lore,
    get_skill_manager,
)

log = logging.getLogger("hearth.nightshift")


async def run_nightshift() -> None:
    """Autonomous nightshift loop with homestead integration."""

    # --- infrastructure setup -------------------------------------------------
    wt = setup_watchtower(HOMESTEAD_DATA_DIR)
    log.info("Nightshift starting with homestead integration")

    # --- context loading ------------------------------------------------------
    lore = read_lore(LORE_DIR)
    skills = get_skill_manager(HOMESTEAD_DATA_DIR)

    if DEFAULT_CHAT_ID:
        send_to_telegram(
            DEFAULT_CHAT_ID,
            "Nightshift starting. I'll work on pending tasks and report back.",
            agent_name="nightshift",
            homestead_data_dir=HOMESTEAD_DATA_DIR,
        )

    skill_count = len(skills.list_skills())
    log.info(
        "Nightshift initialized — lore: %d files, skills: %d",
        len(lore),
        skill_count,
    )

    # --- main loop ------------------------------------------------------------
    # The actual nightshift work loop goes here.  For now this is a skeleton
    # that demonstrates the integration points and keeps the daemon alive.
    while True:
        log.debug("Nightshift tick at %s", time.strftime("%H:%M:%S"))
        await asyncio.sleep(300)  # 5-minute tick


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_nightshift())
