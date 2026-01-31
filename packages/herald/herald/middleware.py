from __future__ import annotations

import logging
import time
from collections import defaultdict

from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

log = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Simple per-user rate limiting."""

    def __init__(self, rate_limit: float = 1.0, max_burst: int = 5):
        self._rate_limit = rate_limit  # min seconds between messages
        self._max_burst = max_burst
        self._timestamps: dict[int, list[float]] = defaultdict(list)

    async def __call__(self, handler, event: types.Message, data: dict):
        user_id = event.from_user.id if event.from_user else 0
        now = time.time()

        # Clean old timestamps
        self._timestamps[user_id] = [
            t for t in self._timestamps[user_id]
            if now - t < 60
        ]

        if len(self._timestamps[user_id]) >= self._max_burst:
            log.warning("Rate limited user %d", user_id)
            await event.answer("Slow down! Too many messages.")
            return

        self._timestamps[user_id].append(now)
        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """Log all incoming messages."""

    async def __call__(self, handler, event: types.Message, data: dict):
        user = event.from_user
        user_info = f"{user.id}" if user else "unknown"
        msg_type = "voice" if event.voice else "text" if event.text else "other"
        msg_preview = (event.text or "")[:50] if event.text else f"[{msg_type}]"

        log.info("msg from=%s type=%s: %s", user_info, msg_type, msg_preview)

        result = await handler(event, data)

        return result
