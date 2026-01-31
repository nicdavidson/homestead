from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path


def _init_watchtower(homestead_data_dir: str = "~/.homestead"):
    """Try to initialize watchtower logging. Returns Watchtower or None."""
    common_pkg = Path(__file__).resolve().parent.parent.parent / "common"
    if str(common_pkg) not in sys.path:
        sys.path.insert(0, str(common_pkg))
    try:
        from common.watchtower import Watchtower, WatchtowerHandler

        db_path = Path(homestead_data_dir).expanduser() / "watchtower.db"
        wt = Watchtower(str(db_path))
        handler = WatchtowerHandler(wt, source="almanac")
        logging.getLogger().addHandler(handler)
        return wt
    except ImportError:
        return None


async def run():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("almanac")

    homestead_dir = "~/.homestead"
    _init_watchtower(homestead_dir)

    from almanac.store import JobStore
    from almanac.scheduler import Scheduler

    store = JobStore(homestead_dir)
    scheduler = Scheduler(store, homestead_dir)

    log.info("Almanac scheduler starting")
    await scheduler.run()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
