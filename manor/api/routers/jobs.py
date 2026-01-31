"""Job scheduler endpoints — reads/writes from the shared almanac jobs.db."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import settings

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    schedule_type TEXT NOT NULL,
    schedule_value TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_config_json TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    last_run_at REAL,
    next_run_at REAL,
    run_count INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    tags_json TEXT DEFAULT '[]',
    source TEXT DEFAULT 'almanac'
)
"""

_CREATE_INDEX = """\
CREATE INDEX IF NOT EXISTS idx_jobs_next_run ON jobs (enabled, next_run_at)
"""


def _db_path() -> Path:
    return Path(settings.homestead_data_dir).expanduser() / "almanac" / "jobs.db"


def _get_conn() -> sqlite3.Connection:
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    # Ensure table exists (idempotent)
    conn.execute(_CREATE_TABLE)
    conn.execute(_CREATE_INDEX)
    conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] or "",
        "schedule_type": row["schedule_type"],
        "schedule_value": row["schedule_value"],
        "action_type": row["action_type"],
        "action_config": json.loads(row["action_config_json"]),
        "enabled": bool(row["enabled"]),
        "last_run_at": row["last_run_at"],
        "next_run_at": row["next_run_at"],
        "run_count": row["run_count"] or 0,
        "created_at": row["created_at"],
        "tags": json.loads(row["tags_json"]) if row["tags_json"] else [],
        "source": row["source"] or "almanac",
    }


# ---------------------------------------------------------------------------
# Cron helpers (duplicated from almanac.store so manor has no dependency)
# ---------------------------------------------------------------------------


def _parse_cron_field(field: str, min_val: int, max_val: int) -> list[int]:
    values: set[int] = set()
    for part in field.split(","):
        part = part.strip()
        step = 1
        if "/" in part:
            part, step_str = part.split("/", 1)
            step = int(step_str)
        if part == "*":
            values.update(range(min_val, max_val + 1, step))
        elif "-" in part:
            lo, hi = part.split("-", 1)
            values.update(range(int(lo), int(hi) + 1, step))
        else:
            values.add(int(part))
    return sorted(values)


def _compute_next_cron(expression: str, after: float | None = None) -> float:
    import calendar
    from datetime import datetime, timedelta, timezone

    if after is None:
        after = time.time()

    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {expression!r}")

    minutes = _parse_cron_field(parts[0], 0, 59)
    hours = _parse_cron_field(parts[1], 0, 23)
    days_of_month = _parse_cron_field(parts[2], 1, 31)
    months = _parse_cron_field(parts[3], 1, 12)
    days_of_week = _parse_cron_field(parts[4], 0, 6)

    dt = datetime.fromtimestamp(after, tz=timezone.utc).replace(second=0, microsecond=0)
    dt += timedelta(minutes=1)

    limit = after + 2 * 365 * 86400
    while dt.timestamp() < limit:
        if dt.month not in months:
            if dt.month == 12:
                dt = dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0)
            else:
                dt = dt.replace(month=dt.month + 1, day=1, hour=0, minute=0)
            continue
        max_day = calendar.monthrange(dt.year, dt.month)[1]
        if dt.day not in days_of_month or dt.day > max_day:
            dt += timedelta(days=1)
            dt = dt.replace(hour=0, minute=0)
            continue
        if dt.weekday() not in days_of_week:
            dt += timedelta(days=1)
            dt = dt.replace(hour=0, minute=0)
            continue
        if dt.hour not in hours:
            dt += timedelta(hours=1)
            dt = dt.replace(minute=0)
            continue
        if dt.minute not in minutes:
            dt += timedelta(minutes=1)
            continue
        return dt.timestamp()

    raise ValueError(f"Could not compute next run for cron: {expression!r}")


def _compute_next_run(schedule_type: str, schedule_value: str, after: float | None = None) -> float | None:
    now = after if after is not None else time.time()
    if schedule_type == "cron":
        return _compute_next_cron(schedule_value, after=now)
    if schedule_type == "interval":
        return now + float(schedule_value)
    if schedule_type == "once":
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(schedule_value)
            ts = dt.timestamp()
            if ts > now:
                return ts
        except ValueError:
            ts = float(schedule_value)
            if ts > now:
                return ts
        return None
    return None


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class JobCreate(BaseModel):
    name: str
    description: str = ""
    schedule_type: str = Field(..., pattern="^(cron|interval|once)$")
    schedule_value: str
    action_type: str = Field(..., pattern="^(outbox|command|webhook)$")
    action_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    source: str = "manor"


class JobUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    schedule_type: str | None = Field(None, pattern="^(cron|interval|once)$")
    schedule_value: str | None = None
    action_type: str | None = Field(None, pattern="^(outbox|command|webhook)$")
    action_config: dict[str, Any] | None = None
    enabled: bool | None = None
    tags: list[str] | None = None


class ToggleBody(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/summary")
def job_summary():
    """Count of jobs by schedule_type and enabled/disabled."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT schedule_type, enabled, COUNT(*) as cnt "
            "FROM jobs GROUP BY schedule_type, enabled"
        ).fetchall()

        result: dict[str, Any] = {
            "by_schedule_type": {},
            "enabled": 0,
            "disabled": 0,
            "total": 0,
        }
        for row in rows:
            stype = row["schedule_type"]
            count = row["cnt"]
            result["by_schedule_type"].setdefault(stype, 0)
            result["by_schedule_type"][stype] += count
            if row["enabled"]:
                result["enabled"] += count
            else:
                result["disabled"] += count
            result["total"] += count
        return result
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return {"by_schedule_type": {}, "enabled": 0, "disabled": 0, "total": 0}
        raise
    finally:
        conn.close()


@router.get("")
def list_jobs(
    enabled_only: bool = Query(False, description="Only return enabled jobs"),
):
    """List all scheduled jobs."""
    conn = _get_conn()
    try:
        if enabled_only:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE enabled = 1 ORDER BY created_at"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return []
        raise
    finally:
        conn.close()


@router.get("/{job_id}")
def get_job(job_id: str):
    """Get a single job by ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        return _row_to_dict(row)
    finally:
        conn.close()


@router.post("", status_code=201)
def create_job(body: JobCreate):
    """Create a new scheduled job."""
    job_id = str(uuid.uuid4())
    now = time.time()

    try:
        next_run = _compute_next_run(body.schedule_type, body.schedule_value)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid schedule: {exc}")

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO jobs "
            "(id, name, description, schedule_type, schedule_value, "
            "action_type, action_config_json, enabled, last_run_at, "
            "next_run_at, run_count, created_at, tags_json, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, ?, ?, ?)",
            (
                job_id,
                body.name,
                body.description,
                body.schedule_type,
                body.schedule_value,
                body.action_type,
                json.dumps(body.action_config),
                1 if body.enabled else 0,
                next_run,
                now,
                json.dumps(body.tags),
                body.source,
            ),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


@router.put("/{job_id}")
def update_job(job_id: str, body: JobUpdate):
    """Update an existing job (partial update)."""
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

        # Build SET clauses from provided fields
        updates: list[str] = []
        params: list[Any] = []

        if body.name is not None:
            updates.append("name = ?")
            params.append(body.name)
        if body.description is not None:
            updates.append("description = ?")
            params.append(body.description)
        if body.schedule_type is not None:
            updates.append("schedule_type = ?")
            params.append(body.schedule_type)
        if body.schedule_value is not None:
            updates.append("schedule_value = ?")
            params.append(body.schedule_value)
        if body.action_type is not None:
            updates.append("action_type = ?")
            params.append(body.action_type)
        if body.action_config is not None:
            updates.append("action_config_json = ?")
            params.append(json.dumps(body.action_config))
        if body.enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if body.enabled else 0)
        if body.tags is not None:
            updates.append("tags_json = ?")
            params.append(json.dumps(body.tags))

        if not updates:
            # Nothing to update
            return _row_to_dict(existing)

        # Recompute next_run_at if schedule changed
        stype = body.schedule_type if body.schedule_type is not None else existing["schedule_type"]
        sval = body.schedule_value if body.schedule_value is not None else existing["schedule_value"]
        if body.schedule_type is not None or body.schedule_value is not None:
            try:
                next_run = _compute_next_run(stype, sval)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Invalid schedule: {exc}")
            updates.append("next_run_at = ?")
            params.append(next_run)

        params.append(job_id)
        sql = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
        conn.execute(sql, params)
        conn.commit()

        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


@router.put("/{job_id}/toggle")
def toggle_job(job_id: str, body: ToggleBody):
    """Enable or disable a job."""
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

        if body.enabled:
            # Recompute next_run_at on re-enable
            try:
                next_run = _compute_next_run(
                    existing["schedule_type"], existing["schedule_value"]
                )
            except Exception:
                next_run = None
            conn.execute(
                "UPDATE jobs SET enabled = 1, next_run_at = ? WHERE id = ?",
                (next_run, job_id),
            )
        else:
            conn.execute("UPDATE jobs SET enabled = 0 WHERE id = ?", (job_id,))

        conn.commit()

        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


@router.delete("/{job_id}")
def delete_job(job_id: str):
    """Delete a job."""
    conn = _get_conn()
    try:
        existing = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        return {"deleted": True, "id": job_id}
    finally:
        conn.close()


@router.post("/{job_id}/run")
async def run_job(job_id: str):
    """Manually trigger a job (execute its action immediately)."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    finally:
        conn.close()

    # Import and use the scheduler to execute the action
    import sys

    almanac_pkg = Path(__file__).resolve().parent.parent.parent / "packages" / "almanac"
    if str(almanac_pkg) not in sys.path:
        sys.path.insert(0, str(almanac_pkg))

    try:
        from almanac.store import JobStore
        from almanac.scheduler import Scheduler

        store = JobStore(settings.homestead_data_dir)
        scheduler = Scheduler(store, settings.homestead_data_dir)
        success = await scheduler.execute_job(job_id)
    except ImportError:
        # Fall back: just mark the run without executing
        now = time.time()
        conn = _get_conn()
        try:
            conn.execute(
                "UPDATE jobs SET last_run_at = ?, run_count = run_count + 1 WHERE id = ?",
                (now, job_id),
            )
            conn.commit()
        finally:
            conn.close()
        return {"executed": False, "id": job_id, "note": "almanac package not available, marked run only"}

    if success:
        # Re-read to get updated state
        conn = _get_conn()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return {"executed": True, "job": _row_to_dict(row) if row else None}
        finally:
            conn.close()
    else:
        raise HTTPException(status_code=500, detail="Job execution failed")
