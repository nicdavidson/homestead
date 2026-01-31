from __future__ import annotations

import asyncio
import atexit
import fcntl
import logging
import os
import signal
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

_PID_FILE: Path | None = None
_lock_fd: int | None = None


def _acquire_pid_lock(data_dir: str) -> None:
    """Ensure only one Herald instance runs. Dies immediately if another is alive."""
    global _PID_FILE, _lock_fd

    pid_dir = Path(data_dir).expanduser()
    pid_dir.mkdir(parents=True, exist_ok=True)
    _PID_FILE = pid_dir / "herald.pid"

    _lock_fd = os.open(str(_PID_FILE), os.O_WRONLY | os.O_CREAT, 0o644)
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        # Another instance holds the lock — read its PID for the error message
        try:
            existing_pid = Path(str(_PID_FILE)).read_text().strip()
        except Exception:
            existing_pid = "unknown"
        os.close(_lock_fd)
        log.error("Herald is already running (PID %s). Exiting.", existing_pid)
        sys.exit(1)

    # Write our PID and keep the fd open (lock held for process lifetime)
    os.ftruncate(_lock_fd, 0)
    os.write(_lock_fd, f"{os.getpid()}\n".encode())
    os.fsync(_lock_fd)

    atexit.register(_release_pid_lock)


def _release_pid_lock() -> None:
    global _lock_fd
    if _lock_fd is not None:
        try:
            os.close(_lock_fd)
        except OSError:
            pass
        _lock_fd = None
    if _PID_FILE is not None:
        _PID_FILE.unlink(missing_ok=True)


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

    # Single-instance guard
    _acquire_pid_lock(config.homestead_data_dir)

    # Initialize watchtower (structured logging)
    wt = _init_watchtower(config.homestead_data_dir)

    sessions = SessionManager(config)
    queue = MessageQueue(config.max_queue_size)
    bot, dp = create_bot(config, sessions, queue, watchtower=wt)

        # Log active session on startup
    active = sessions.get_active(0)
    if active:
        log.info(f"Herald is running (active session: {active.name})")
    else:
        log.info("Herald is running (no active session)")

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
