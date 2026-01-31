from __future__ import annotations
import json
import os
import sqlite3
import time
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/events", tags=["events"])
HOMESTEAD_DIR = Path(os.environ.get("HOMESTEAD_DATA_DIR", "~/.homestead")).expanduser()

def _get_conn():
    db_path = HOMESTEAD_DIR / "events.db"
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn

@router.get("")
async def list_events(pattern: str | None = None, source: str | None = None, hours: float = 24, limit: int = 100):
    conn = _get_conn()
    if not conn:
        return []
    since = time.time() - hours * 3600
    query = "SELECT * FROM events WHERE timestamp >= ?"
    params = [since]
    if source:
        query += " AND source = ?"
        params.append(source)
    if pattern and "*" not in pattern:
        query += " AND topic = ?"
        params.append(pattern)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    results = []
    for r in rows:
        event = dict(r)
        event["payload"] = json.loads(event["payload"]) if event.get("payload") else {}
        if pattern and "*" in pattern:
            import fnmatch
            if not fnmatch.fnmatch(event["topic"], pattern):
                continue
        results.append(event)
    return results
