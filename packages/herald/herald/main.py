from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from herald.config import load_config
from herald.sessions import SessionManager
from herald.queue import MessageQueue
from herald.bot import create_bot, poll_outbox

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("herald")


def _init_watchtower(homestead_data_dir: str):
    """Try to initialize watchtower logging. Returns Watchtower or None."""
    # Add common package to sys.path
    common_pkg = Path(__file__).resolve().parent.parent.parent / "common"
    if str(common_pkg) not in sys.path:
        sys.path.insert(0, str(common_pkg))

    try:
        from common.watchtower import Watchtower, WatchtowerHandler

        db_path = Path(homestead_data_dir).expanduser() / "watchtower.db"
        wt = Watchtower(str(db_path))
        handler = WatchtowerHandler(wt, source="herald")
        logging.getLogger().addHandler(handler)
        log.info("Watchtower logging enabled (%s)", db_path)
        return wt
    except ImportError:
        log.warning("common package not found, watchtower disabled")
        return None


async def run() -> None:
    config = load_config()

    # Initialize watchtower (structured logging)
    wt = _init_watchtower(config.homestead_data_dir)

    sessions = SessionManager(config)
    queue = MessageQueue(config.max_queue_size)
    bot, dp = create_bot(config, sessions, queue, watchtower=wt)

    log.info("Herald is running")

    # Start outbox poller (delivers messages from other packages)
    asyncio.create_task(poll_outbox(bot, config))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
