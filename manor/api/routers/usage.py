"""Usage monitoring endpoints — tracks token usage and costs."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

from fastapi import APIRouter, Query

from ..config import settings

router = APIRouter(prefix="/api/usage", tags=["usage"])

# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS usage_records (
    id                    TEXT PRIMARY KEY,
    session_id            TEXT NOT NULL,
    chat_id               INTEGER NOT NULL,
    session_name          TEXT NOT NULL DEFAULT '',
    model                 TEXT NOT NULL DEFAULT '',
    input_tokens          INTEGER NOT NULL DEFAULT 0,
    output_tokens         INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens     INTEGER NOT NULL DEFAULT 0,
    total_tokens          INTEGER NOT NULL DEFAULT 0,
    cost_usd              REAL,
    num_turns             INTEGER NOT NULL DEFAULT 0,
    source                TEXT NOT NULL DEFAULT 'chat',
    started_at            REAL NOT NULL,
    completed_at          REAL,
    recorded_at           REAL NOT NULL,
    extra_json            TEXT DEFAULT '{}'
)
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_usage_session ON usage_records (session_id)",
    "CREATE INDEX IF NOT EXISTS idx_usage_chat ON usage_records (chat_id)",
    "CREATE INDEX IF NOT EXISTS idx_usage_model ON usage_records (model)",
    "CREATE INDEX IF NOT EXISTS idx_usage_started ON usage_records (started_at)",
    "CREATE INDEX IF NOT EXISTS idx_usage_source ON usage_records (source)",
]

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    db = settings.usage_db
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE)
    for idx in _CREATE_INDEXES:
        conn.execute(idx)
    conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "chat_id": row["chat_id"],
        "session_name": row["session_name"],
        "model": row["model"],
        "input_tokens": row["input_tokens"],
        "output_tokens": row["output_tokens"],
        "cache_creation_tokens": row["cache_creation_tokens"],
        "cache_read_tokens": row["cache_read_tokens"],
        "total_tokens": row["total_tokens"],
        "cost_usd": row["cost_usd"],
        "num_turns": row["num_turns"],
        "source": row["source"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "recorded_at": row["recorded_at"],
        "extra": json.loads(row["extra_json"]) if row["extra_json"] else {},
    }


# ---------------------------------------------------------------------------
# Public API — record_usage (importable from chat.py)
# ---------------------------------------------------------------------------


def record_usage(
    *,
    session_id: str,
    chat_id: int,
    session_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    cost_usd: float | None = None,
    num_turns: int = 0,
    source: str = "chat",
    started_at: float,
    completed_at: float | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Insert a usage record. Returns the record ID."""
    record_id = str(uuid.uuid4())
    now = time.time()
    total = input_tokens + output_tokens
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO usage_records "
            "(id, session_id, chat_id, session_name, model, "
            "input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, "
            "total_tokens, cost_usd, num_turns, source, "
            "started_at, completed_at, recorded_at, extra_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                record_id, session_id, chat_id, session_name, model,
                input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens,
                total, cost_usd, num_turns, source,
                started_at, completed_at or now, now,
                json.dumps(extra or {}),
            ),
        )
        conn.commit()
        return record_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_usage(
    session_id: str | None = Query(None),
    chat_id: int | None = Query(None),
    model: str | None = Query(None),
    source: str | None = Query(None),
    since: float | None = Query(None, description="Unix timestamp"),
    until: float | None = Query(None, description="Unix timestamp"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List usage records with optional filters."""
    conn = _get_conn()
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if chat_id is not None:
            clauses.append("chat_id = ?")
            params.append(chat_id)
        if model:
            clauses.append("model = ?")
            params.append(model)
        if source:
            clauses.append("source = ?")
            params.append(source)
        if since is not None:
            clauses.append("started_at >= ?")
            params.append(since)
        if until is not None:
            clauses.append("started_at <= ?")
            params.append(until)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM usage_records {where}", params
        ).fetchone()
        total = count_row["cnt"] if count_row else 0

        rows = conn.execute(
            f"SELECT * FROM usage_records {where} ORDER BY started_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

        return {"total": total, "records": [_row_to_dict(r) for r in rows]}
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return {"total": 0, "records": []}
        raise
    finally:
        conn.close()


@router.get("/summary")
def usage_summary(
    since: float | None = Query(None),
    until: float | None = Query(None),
):
    """Aggregate usage summary."""
    conn = _get_conn()
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if since:
            clauses.append("started_at >= ?")
            params.append(since)
        if until:
            clauses.append("started_at <= ?")
            params.append(until)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        row = conn.execute(
            f"""SELECT
                COUNT(*) as total_records,
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                COALESCE(SUM(cache_creation_tokens), 0) as total_cache_creation,
                COALESCE(SUM(cache_read_tokens), 0) as total_cache_read,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as total_cost_usd,
                COALESCE(SUM(num_turns), 0) as total_turns,
                MIN(started_at) as earliest,
                MAX(started_at) as latest
            FROM usage_records {where}""",
            params,
        ).fetchone()

        return {
            "total_records": row["total_records"],
            "total_input_tokens": row["total_input_tokens"],
            "total_output_tokens": row["total_output_tokens"],
            "total_cache_creation": row["total_cache_creation"],
            "total_cache_read": row["total_cache_read"],
            "total_tokens": row["total_tokens"],
            "total_cost_usd": row["total_cost_usd"],
            "total_turns": row["total_turns"],
            "earliest": row["earliest"],
            "latest": row["latest"],
        }
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return {
                "total_records": 0, "total_input_tokens": 0,
                "total_output_tokens": 0, "total_cache_creation": 0,
                "total_cache_read": 0, "total_tokens": 0,
                "total_cost_usd": 0, "total_turns": 0,
                "earliest": None, "latest": None,
            }
        raise
    finally:
        conn.close()


@router.get("/by-model")
def usage_by_model(
    since: float | None = Query(None),
    until: float | None = Query(None),
):
    """Usage breakdown grouped by model."""
    conn = _get_conn()
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if since:
            clauses.append("started_at >= ?")
            params.append(since)
        if until:
            clauses.append("started_at <= ?")
            params.append(until)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = conn.execute(
            f"""SELECT model,
                COUNT(*) as records,
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as cost_usd
            FROM usage_records {where}
            GROUP BY model ORDER BY cost_usd DESC""",
            params,
        ).fetchall()

        return [dict(r) for r in rows]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return []
        raise
    finally:
        conn.close()


@router.get("/timeseries")
def usage_timeseries(
    since: float | None = Query(None),
    until: float | None = Query(None),
    bucket: str = Query("day", pattern="^(hour|day|week)$"),
):
    """Time-series usage data bucketed by hour/day/week."""
    now = time.time()
    if since is None:
        since = now - (30 * 86400)
    if until is None:
        until = now

    bucket_expr = {
        "hour": "strftime('%Y-%m-%d %H:00', started_at, 'unixepoch')",
        "day": "strftime('%Y-%m-%d', started_at, 'unixepoch')",
        "week": "strftime('%Y-%W', started_at, 'unixepoch')",
    }[bucket]

    conn = _get_conn()
    try:
        rows = conn.execute(
            f"""SELECT {bucket_expr} as bucket,
                COUNT(*) as records,
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as cost_usd,
                COALESCE(SUM(num_turns), 0) as turns
            FROM usage_records
            WHERE started_at >= ? AND started_at <= ?
            GROUP BY bucket ORDER BY bucket""",
            (since, until),
        ).fetchall()

        return [dict(r) for r in rows]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return []
        raise
    finally:
        conn.close()


@router.get("/by-session")
def usage_by_session(
    since: float | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Usage breakdown per session, ordered by total cost descending."""
    conn = _get_conn()
    try:
        clauses: list[str] = []
        params: list[Any] = []
        if since:
            clauses.append("started_at >= ?")
            params.append(since)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        rows = conn.execute(
            f"""SELECT session_id, session_name, chat_id,
                COUNT(*) as records,
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(cost_usd), 0) as cost_usd,
                MAX(started_at) as last_used
            FROM usage_records {where}
            GROUP BY session_id ORDER BY cost_usd DESC LIMIT ?""",
            params + [limit],
        ).fetchall()

        return [dict(r) for r in rows]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return []
        raise
    finally:
        conn.close()
