from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    chat_id: int
    user_id: int
    text: str
    timestamp: float


class MessageQueue:
    def __init__(self, max_size: int) -> None:
        self._max_size = max_size
        self._queues: dict[int, list[QueuedMessage]] = {}
        self._active: set[int] = set()

    def enqueue(self, msg: QueuedMessage) -> bool:
        queue = self._queues.setdefault(msg.chat_id, [])
        if len(queue) >= self._max_size:
            log.warning("chat=%d queue full (depth=%d, max=%d)", msg.chat_id, len(queue), self._max_size)
            return False
        queue.append(msg)
        log.debug("chat=%d enqueued (depth=%d)", msg.chat_id, len(queue))
        return True

    def dequeue(self, chat_id: int) -> QueuedMessage | None:
        queue = self._queues.get(chat_id)
        if not queue:
            return None
        msg = queue.pop(0)
        log.debug("chat=%d dequeued (remaining=%d)", chat_id, len(queue))
        return msg

    def mark_active(self, chat_id: int) -> None:
        self._active.add(chat_id)
        log.debug("chat=%d queue active", chat_id)

    def mark_idle(self, chat_id: int) -> None:
        self._active.discard(chat_id)
        log.debug("chat=%d queue idle", chat_id)

    def is_active(self, chat_id: int) -> bool:
        return chat_id in self._active

    def clear(self, chat_id: int) -> None:
        removed = len(self._queues.get(chat_id, []))
        self._queues.pop(chat_id, None)
        if removed:
            log.info("chat=%d queue cleared (%d messages dropped)", chat_id, removed)
