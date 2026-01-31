from __future__ import annotations
import os
import sqlite3
import time
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/outbox", tags=["outbox"])
HOMESTEAD_DIR = Path(os.environ.get("HOMESTEAD_DATA_DIR", "~/.homestead")).expanduser()

def _get_conn():
    db_path = HOMESTEAD_DIR / "outbox.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    # Ensure table
    conn.execute("""CREATE TABLE IF NOT EXISTS outbox (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        agent_name TEXT NOT NULL, message TEXT NOT NULL,
        parse_mode TEXT DEFAULT 'HTML', created_at REAL NOT NULL,
        sent_at REAL, status TEXT DEFAULT 'pending'
    )""")
    return conn

@router.get("")
async def list_outbox(status: str | None = None, agent: str | None = None, limit: int = 50):
    conn = _get_conn()
    query = "SELECT * FROM outbox WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if agent:
        query += " AND agent_name = ?"
        params.append(agent)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

class OutboxCreate(BaseModel):
    chat_id: int
    agent_name: str
    message: str

@router.post("")
async def create_outbox_message(data: OutboxCreate):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO outbox (chat_id, agent_name, message, created_at) VALUES (?, ?, ?, ?)",
        (data.chat_id, data.agent_name, data.message, time.time())
    )
    conn.commit()
    conn.close()
    return {"status": "created"}
