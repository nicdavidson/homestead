from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from common.db import get_connection


_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS outbox (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER NOT NULL,
    agent_name TEXT    NOT NULL,
    message    TEXT    NOT NULL,
    parse_mode TEXT    DEFAULT 'HTML',
    created_at REAL    NOT NULL,
    sent_at    REAL,
    status     TEXT    DEFAULT 'pending'
)
"""

_CREATE_INDEX = """\
CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox (status, created_at)
"""


@dataclass
class OutboxMessage:
    id: int
    chat_id: int
    agent_name: str
    message: str
    parse_mode: str
    created_at: float


def _ensure_table(db_path: str | Path) -> None:
    conn = get_connection(db_path)
    conn.execute(_CREATE_TABLE)
    conn.execute(_CREATE_INDEX)
    conn.commit()
    conn.close()


def post_message(
    db_path: str | Path,
    chat_id: int,
    agent_name: str,
    message: str,
    parse_mode: str = "HTML",
) -> None:
    """Insert a message into the outbox for herald to deliver."""
    conn = get_connection(db_path)
    conn.execute(_CREATE_TABLE)
    conn.execute(
        "INSERT INTO outbox (chat_id, agent_name, message, parse_mode, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (chat_id, agent_name, message, parse_mode, time.time()),
    )
    conn.commit()
    conn.close()


def get_pending(db_path: str | Path, limit: int = 20) -> list[OutboxMessage]:
    """Fetch pending outbox messages."""
    conn = get_connection(db_path)
    conn.execute(_CREATE_TABLE)
    rows = conn.execute(
        "SELECT id, chat_id, agent_name, message, parse_mode, created_at "
        "FROM outbox WHERE status = 'pending' ORDER BY created_at LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        OutboxMessage(
            id=r["id"],
            chat_id=r["chat_id"],
            agent_name=r["agent_name"],
            message=r["message"],
            parse_mode=r["parse_mode"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def mark_sent(db_path: str | Path, msg_id: int) -> None:
    """Mark an outbox message as sent."""
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE outbox SET status = 'sent', sent_at = ? WHERE id = ?",
        (time.time(), msg_id),
    )
    conn.commit()
    conn.close()


def mark_failed(db_path: str | Path, msg_id: int) -> None:
    """Mark an outbox message as failed."""
    conn = get_connection(db_path)
    conn.execute("UPDATE outbox SET status = 'failed' WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()
