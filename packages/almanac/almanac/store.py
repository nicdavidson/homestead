from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from almanac.models import Job, JobAction, JobStatus, Schedule, ScheduleType


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


def _parse_cron_field(field: str, min_val: int, max_val: int) -> list[int]:
    """Parse a single cron field into a list of matching integer values."""
    values: set[int] = set()

    for part in field.split(","):
        part = part.strip()

        # Handle step values: */5, 1-10/2
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


def compute_next_cron(expression: str, after: float | None = None) -> float:
    """Compute the next timestamp that matches a cron expression.

    Expression format: minute hour day_of_month month day_of_week
    Supports: *, ranges (1-5), steps (*/15), lists (1,3,5).
    """
    import calendar
    from datetime import datetime, timezone

    if after is None:
        after = time.time()

    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (need 5 fields): {expression!r}")

    minutes = _parse_cron_field(parts[0], 0, 59)
    hours = _parse_cron_field(parts[1], 0, 23)
    days_of_month = _parse_cron_field(parts[2], 1, 31)
    months = _parse_cron_field(parts[3], 1, 12)
    days_of_week = _parse_cron_field(parts[4], 0, 6)  # 0=Monday in Python

    dt = datetime.fromtimestamp(after, tz=timezone.utc).replace(second=0, microsecond=0)

    # Move one minute forward so we don't match the current minute
    from datetime import timedelta
    dt += timedelta(minutes=1)

    # Search up to 2 years ahead
    limit = after + 2 * 365 * 86400
    while dt.timestamp() < limit:
        if dt.month not in months:
            # Skip to first day of next month
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

        # Python weekday: Monday=0 .. Sunday=6
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


def compute_next_run(schedule_type: str, schedule_value: str, after: float | None = None) -> float | None:
    """Compute the next run timestamp for a given schedule."""
    now = after if after is not None else time.time()

    if schedule_type == "cron":
        return compute_next_cron(schedule_value, after=now)

    if schedule_type == "interval":
        interval_seconds = float(schedule_value)
        return now + interval_seconds

    if schedule_type == "once":
        from datetime import datetime, timezone
        # ISO datetime string
        try:
            dt = datetime.fromisoformat(schedule_value)
            ts = dt.timestamp()
            if ts > now:
                return ts
        except ValueError:
            # Try as a raw timestamp
            ts = float(schedule_value)
            if ts > now:
                return ts
        return None

    return None


class JobStore:
    """SQLite-backed storage for scheduled jobs."""

    def __init__(self, homestead_dir: str = "~/.homestead") -> None:
        db_dir = Path(homestead_dir).expanduser() / "almanac"
        db_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = db_dir / "jobs.db"
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute(_CREATE_TABLE)
            conn.execute(_CREATE_INDEX)
            conn.commit()
        finally:
            conn.close()

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        """Convert a database row to a Job dataclass."""
        schedule_type_str = row["schedule_type"]
        try:
            stype = ScheduleType(schedule_type_str)
        except ValueError:
            stype = ScheduleType.CRON

        schedule = Schedule(type=stype, expression=row["schedule_value"])
        action = JobAction(
            type=row["action_type"],
            config=json.loads(row["action_config_json"]),
        )

        enabled = bool(row["enabled"])
        if not enabled:
            status = JobStatus.DISABLED
        elif schedule_type_str == "once" and row["run_count"] and row["run_count"] > 0:
            status = JobStatus.COMPLETED
        else:
            status = JobStatus.ACTIVE

        return Job(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            schedule=schedule,
            action=action,
            status=status,
            last_run_at=row["last_run_at"],
            next_run_at=row["next_run_at"],
            run_count=row["run_count"] or 0,
            created_at=row["created_at"],
            tags=json.loads(row["tags_json"]) if row["tags_json"] else [],
            source=row["source"] or "almanac",
        )

    def _job_to_params(self, job: Job) -> dict:
        """Convert a Job to parameters for an INSERT/REPLACE."""
        schedule_type = job.schedule.type.value if job.schedule else "cron"
        schedule_value = job.schedule.expression if job.schedule else ""
        action_type = job.action.type if job.action else "command"
        action_config = json.dumps(job.action.config if job.action else {})
        enabled = 1 if job.status in (JobStatus.ACTIVE,) else 0

        return {
            "id": job.id,
            "name": job.name,
            "description": job.description,
            "schedule_type": schedule_type,
            "schedule_value": schedule_value,
            "action_type": action_type,
            "action_config_json": action_config,
            "enabled": enabled,
            "last_run_at": job.last_run_at,
            "next_run_at": job.next_run_at,
            "run_count": job.run_count,
            "created_at": job.created_at,
            "tags_json": json.dumps(job.tags),
            "source": job.source,
        }

    def save(self, job: Job) -> None:
        """Insert or replace a job in the database."""
        # Compute next_run_at if not set
        if job.next_run_at is None and job.schedule:
            job.next_run_at = compute_next_run(
                job.schedule.type.value, job.schedule.expression
            )

        params = self._job_to_params(job)
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO jobs "
                "(id, name, description, schedule_type, schedule_value, "
                "action_type, action_config_json, enabled, last_run_at, "
                "next_run_at, run_count, created_at, tags_json, source) "
                "VALUES (:id, :name, :description, :schedule_type, :schedule_value, "
                ":action_type, :action_config_json, :enabled, :last_run_at, "
                ":next_run_at, :run_count, :created_at, :tags_json, :source)",
                params,
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, job_id: str) -> Job | None:
        """Retrieve a single job by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_job(row)
        finally:
            conn.close()

    def list_jobs(self, enabled_only: bool = False) -> list[Job]:
        """List all jobs, optionally filtering to enabled-only."""
        conn = self._get_conn()
        try:
            if enabled_only:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE enabled = 1 ORDER BY created_at"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at"
                ).fetchall()
            return [self._row_to_job(r) for r in rows]
        finally:
            conn.close()

    def delete(self, job_id: str) -> bool:
        """Delete a job by ID. Returns True if a row was deleted."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_due_jobs(self) -> list[Job]:
        """Return all enabled jobs whose next_run_at is in the past."""
        now = time.time()
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE enabled = 1 AND next_run_at <= ? "
                "ORDER BY next_run_at",
                (now,),
            ).fetchall()
            return [self._row_to_job(r) for r in rows]
        finally:
            conn.close()

    def mark_run(self, job_id: str) -> None:
        """Record that a job has just been executed.

        Updates last_run_at, increments run_count, and computes the next
        run time. For 'once' schedules the job is disabled after running.
        """
        now = time.time()
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT schedule_type, schedule_value, run_count FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                return

            schedule_type = row["schedule_type"]
            schedule_value = row["schedule_value"]
            new_run_count = (row["run_count"] or 0) + 1

            next_run = compute_next_run(schedule_type, schedule_value, after=now)

            if schedule_type == "once":
                # One-shot: disable after running
                conn.execute(
                    "UPDATE jobs SET last_run_at = ?, run_count = ?, "
                    "next_run_at = NULL, enabled = 0 WHERE id = ?",
                    (now, new_run_count, job_id),
                )
            else:
                conn.execute(
                    "UPDATE jobs SET last_run_at = ?, run_count = ?, "
                    "next_run_at = ? WHERE id = ?",
                    (now, new_run_count, next_run, job_id),
                )
            conn.commit()
        finally:
            conn.close()

    def toggle(self, job_id: str, enabled: bool) -> bool:
        """Enable or disable a job. Returns True if the job existed."""
        conn = self._get_conn()
        try:
            # If re-enabling, recompute next_run_at
            if enabled:
                row = conn.execute(
                    "SELECT schedule_type, schedule_value FROM jobs WHERE id = ?",
                    (job_id,),
                ).fetchone()
                if row is None:
                    return False
                next_run = compute_next_run(row["schedule_type"], row["schedule_value"])
                cursor = conn.execute(
                    "UPDATE jobs SET enabled = 1, next_run_at = ? WHERE id = ?",
                    (next_run, job_id),
                )
            else:
                cursor = conn.execute(
                    "UPDATE jobs SET enabled = 0 WHERE id = ?",
                    (job_id,),
                )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
