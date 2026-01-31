"""Homestead Event Bus — lightweight pub/sub with SQLite persistence.

Usage:
    from common.events import EventBus

    bus = EventBus("~/.homestead/events.db")

    # Subscribe
    bus.subscribe("task.created", my_handler)

    # Publish
    bus.publish("task.created", {"task_id": "abc", "title": "Do thing"})

    # Query event history
    events = bus.history("task.*", hours=24)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Awaitable, Any

from common.db import get_connection

log = logging.getLogger(__name__)

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  REAL    NOT NULL,
    topic      TEXT    NOT NULL,
    source     TEXT    NOT NULL DEFAULT '',
    payload    TEXT    NOT NULL DEFAULT '{}',
    processed  INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_INDEX = """\
CREATE INDEX IF NOT EXISTS idx_events_topic_ts ON events (topic, timestamp)
"""


@dataclass
class Event:
    id: int
    timestamp: float
    topic: str
    source: str
    payload: dict
    processed: bool = False


Handler = Callable[[Event], Awaitable[None]] | Callable[[Event], None]


class EventBus:
    def __init__(self, db_path: str | Path = "~/.homestead/events.db") -> None:
        self._db_path = Path(db_path).expanduser()
        self._conn = get_connection(self._db_path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.execute(_CREATE_INDEX)
        self._conn.commit()
        self._handlers: dict[str, list[Handler]] = {}

    def subscribe(self, pattern: str, handler: Handler) -> None:
        """Subscribe to events matching a glob pattern (e.g. 'task.*')."""
        self._handlers.setdefault(pattern, []).append(handler)
        log.debug("Subscribed to %s", pattern)

    def publish(self, topic: str, payload: dict | None = None, source: str = "") -> Event:
        """Publish an event. Persists to DB and notifies matching handlers."""
        now = time.time()
        payload = payload or {}

        cursor = self._conn.execute(
            "INSERT INTO events (timestamp, topic, source, payload) VALUES (?, ?, ?, ?)",
            (now, topic, source, json.dumps(payload)),
        )
        self._conn.commit()

        event = Event(
            id=cursor.lastrowid,
            timestamp=now,
            topic=topic,
            source=source,
            payload=payload,
        )

        # Notify handlers
        for pattern, handlers in self._handlers.items():
            if fnmatch.fnmatch(topic, pattern):
                for handler in handlers:
                    try:
                        result = handler(event)
                        if asyncio.iscoroutine(result):
                            # Fire and forget for async handlers
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.ensure_future(result)
                            else:
                                loop.run_until_complete(result)
                    except Exception:
                        log.exception("Event handler error for %s", topic)

        return event

    def history(
        self,
        pattern: str | None = None,
        source: str | None = None,
        hours: float | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Query event history."""
        clauses: list[str] = []
        params: list = []

        if pattern and "*" not in pattern:
            clauses.append("topic = ?")
            params.append(pattern)
        if source:
            clauses.append("source = ?")
            params.append(source)
        if hours:
            clauses.append("timestamp >= ?")
            params.append(time.time() - hours * 3600)

        where = " AND ".join(clauses) if clauses else "1=1"
        sql = f"SELECT * FROM events WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        events = [self._row_to_event(r) for r in rows]

        # Filter by glob pattern if it contains wildcards
        if pattern and "*" in pattern:
            events = [e for e in events if fnmatch.fnmatch(e.topic, pattern)]

        return events

    def mark_processed(self, event_id: int) -> None:
        self._conn.execute("UPDATE events SET processed = 1 WHERE id = ?", (event_id,))
        self._conn.commit()

    def pending(self, topic: str | None = None, limit: int = 50) -> list[Event]:
        """Get unprocessed events."""
        if topic:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE processed = 0 AND topic = ? ORDER BY timestamp LIMIT ?",
                (topic, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE processed = 0 ORDER BY timestamp LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_event(r) for r in rows]

    @staticmethod
    def _row_to_event(row) -> Event:
        return Event(
            id=row["id"],
            timestamp=row["timestamp"],
            topic=row["topic"],
            source=row["source"],
            payload=json.loads(row["payload"]) if row["payload"] else {},
            processed=bool(row["processed"]),
        )
