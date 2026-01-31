from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


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
            return False
        queue.append(msg)
        return True

    def dequeue(self, chat_id: int) -> QueuedMessage | None:
        queue = self._queues.get(chat_id)
        if not queue:
            return None
        return queue.pop(0)

    def mark_active(self, chat_id: int) -> None:
        self._active.add(chat_id)

    def mark_idle(self, chat_id: int) -> None:
        self._active.discard(chat_id)

    def is_active(self, chat_id: int) -> bool:
        return chat_id in self._active

    def clear(self, chat_id: int) -> None:
        self._queues.pop(chat_id, None)
