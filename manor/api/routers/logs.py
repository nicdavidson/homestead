"""Log query endpoints — reads from the shared watchtower.db."""

from __future__ import annotations

import json
import sqlite3
import time

from fastapi import APIRouter, Query

from ..config import settings

router = APIRouter(prefix="/api/logs", tags=["logs"])

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    db_path = settings.watchtower_db
    if not db_path.exists():
        # Return a connection anyway; queries will just return empty results
        pass
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "level": row["level"],
        "source": row["source"],
        "message": row["message"],
        "data": json.loads(row["data_json"]) if row["data_json"] else None,
        "session_id": row["session_id"],
        "chat_id": row["chat_id"],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
def query_logs(
    hours: float = Query(24, description="How many hours back to search"),
    level: str | None = Query(None, description="Filter by log level"),
    source: str | None = Query(None, description="Filter by source prefix"),
    search: str | None = Query(None, description="Search within message text"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows to return"),
):
    """Query logs with flexible filtering."""
    conn = _get_conn()
    try:
        clauses: list[str] = []
        params: list = []

        since = time.time() - hours * 3600
        clauses.append("timestamp >= ?")
        params.append(since)

        if level is not None:
            clauses.append("level = ?")
            params.append(level.upper())

        if source is not None:
            clauses.append("source LIKE ?")
            params.append(f"{source}%")

        if search is not None:
            clauses.append("message LIKE ?")
            params.append(f"%{search}%")

        where = " AND ".join(clauses) if clauses else "1=1"
        sql = f"SELECT * FROM logs WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.OperationalError as exc:
        # Table may not exist yet if watchtower hasn't been initialized
        if "no such table" in str(exc):
            return []
        raise
    finally:
        conn.close()


@router.get("/summary")
def log_summary(
    hours: float = Query(24, description="How many hours back"),
):
    """Summary of logs grouped by source and level."""
    conn = _get_conn()
    try:
        since = time.time() - hours * 3600
        rows = conn.execute(
            "SELECT source, level, COUNT(*) as cnt FROM logs "
            "WHERE timestamp >= ? GROUP BY source, level ORDER BY source, level",
            (since,),
        ).fetchall()

        result: dict[str, dict[str, int]] = {}
        for row in rows:
            src = row["source"].split(".")[0]
            result.setdefault(src, {})[row["level"]] = row["cnt"]
        return result
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return {}
        raise
    finally:
        conn.close()
