"""Health check and metrics endpoints."""
from __future__ import annotations

import os
import platform
import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(tags=["health"])

HOMESTEAD_DIR = Path(os.environ.get("HOMESTEAD_DATA_DIR", "~/.homestead")).expanduser()


def _db_ok(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        conn = sqlite3.connect(str(path), timeout=2)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False


@router.get("/health")
async def health():
    """Basic health check."""
    return {"status": "ok", "timestamp": time.time()}


@router.get("/health/detailed")
async def health_detailed():
    """Detailed health check with component status."""
    databases = {
        "watchtower": HOMESTEAD_DIR / "watchtower.db",
        "outbox": HOMESTEAD_DIR / "outbox.db",
        "tasks": HOMESTEAD_DIR / "steward" / "tasks.db",
        "jobs": HOMESTEAD_DIR / "almanac" / "jobs.db",
        "usage": HOMESTEAD_DIR / "usage.db",
    }

    # Check herald sessions db
    herald_data = Path(os.environ.get("HERALD_DATA_DIR", "")).expanduser()
    if herald_data.is_dir():
        databases["sessions"] = herald_data / "sessions.db"

    db_status = {}
    for name, path in databases.items():
        db_status[name] = {
            "exists": path.exists(),
            "healthy": _db_ok(path),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }

    directories = {
        "skills": HOMESTEAD_DIR / "skills",
        "scratchpad": HOMESTEAD_DIR / "scratchpad",
        "lore": Path(os.environ.get("LORE_DIR", "")).expanduser(),
    }

    dir_status = {}
    for name, path in directories.items():
        if path.is_dir():
            files = list(path.glob("*.md"))
            dir_status[name] = {"exists": True, "file_count": len(files)}
        else:
            dir_status[name] = {"exists": False, "file_count": 0}

    all_healthy = all(d["healthy"] for d in db_status.values() if d["exists"])

    return {
        "status": "ok" if all_healthy else "degraded",
        "timestamp": time.time(),
        "databases": db_status,
        "directories": dir_status,
        "system": {
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "hostname": platform.node(),
        },
    }


@router.get("/metrics")
async def metrics():
    """Aggregated metrics across all homestead components."""
    result = {
        "timestamp": time.time(),
        "logs": {"last_24h": {}, "last_1h": {}, "total": 0},
        "tasks": {"total": 0, "by_status": {}},
        "sessions": {"total": 0, "active": 0, "total_messages": 0},
        "jobs": {"total": 0, "enabled": 0, "total_runs": 0},
        "outbox": {"pending": 0, "sent": 0, "failed": 0},
        "usage": {"records_24h": 0, "tokens_24h": 0, "cost_24h": 0.0},
    }

    # Log metrics
    wt_path = HOMESTEAD_DIR / "watchtower.db"
    if wt_path.exists():
        try:
            conn = sqlite3.connect(str(wt_path))
            conn.row_factory = sqlite3.Row
            since_24h = time.time() - 86400
            since_1h = time.time() - 3600

            rows = conn.execute(
                "SELECT level, COUNT(*) as cnt FROM logs WHERE timestamp >= ? GROUP BY level",
                (since_24h,)
            ).fetchall()
            result["logs"]["last_24h"] = {r["level"]: r["cnt"] for r in rows}

            rows = conn.execute(
                "SELECT level, COUNT(*) as cnt FROM logs WHERE timestamp >= ? GROUP BY level",
                (since_1h,)
            ).fetchall()
            result["logs"]["last_1h"] = {r["level"]: r["cnt"] for r in rows}

            total = conn.execute("SELECT COUNT(*) as cnt FROM logs").fetchone()
            result["logs"]["total"] = total["cnt"] if total else 0
            conn.close()
        except Exception:
            pass

    # Task metrics
    tasks_path = HOMESTEAD_DIR / "steward" / "tasks.db"
    if tasks_path.exists():
        try:
            conn = sqlite3.connect(str(tasks_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status").fetchall()
            by_status = {r["status"]: r["cnt"] for r in rows}
            result["tasks"] = {"by_status": by_status, "total": sum(by_status.values())}
            conn.close()
        except Exception:
            pass

    # Session metrics
    herald_data = Path(os.environ.get("HERALD_DATA_DIR", "")).expanduser()
    sessions_path = herald_data / "sessions.db" if herald_data.is_dir() else None
    if sessions_path and sessions_path.exists():
        try:
            conn = sqlite3.connect(str(sessions_path))
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) as cnt FROM sessions").fetchone()
            active = conn.execute("SELECT COUNT(*) as cnt FROM sessions WHERE is_active = 1").fetchone()
            total_msgs = conn.execute("SELECT SUM(message_count) as cnt FROM sessions").fetchone()
            result["sessions"].update({
                "total": total["cnt"] if total else 0,
                "active": active["cnt"] if active else 0,
                "total_messages": total_msgs["cnt"] if total_msgs and total_msgs["cnt"] else 0,
            })
            conn.close()
        except Exception:
            pass

    # Job metrics
    jobs_path = HOMESTEAD_DIR / "almanac" / "jobs.db"
    if jobs_path.exists():
        try:
            conn = sqlite3.connect(str(jobs_path))
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) as cnt FROM jobs").fetchone()
            enabled = conn.execute("SELECT COUNT(*) as cnt FROM jobs WHERE enabled = 1").fetchone()
            total_runs = conn.execute("SELECT SUM(run_count) as cnt FROM jobs").fetchone()
            result["jobs"].update({
                "total": total["cnt"] if total else 0,
                "enabled": enabled["cnt"] if enabled else 0,
                "total_runs": total_runs["cnt"] if total_runs and total_runs["cnt"] else 0,
            })
            conn.close()
        except Exception:
            pass

    # Outbox metrics
    outbox_path = HOMESTEAD_DIR / "outbox.db"
    if outbox_path.exists():
        try:
            conn = sqlite3.connect(str(outbox_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT status, COUNT(*) as cnt FROM outbox GROUP BY status").fetchall()
            result["outbox"].update({r["status"]: r["cnt"] for r in rows})
            conn.close()
        except Exception:
            pass

    # Usage metrics
    usage_path = HOMESTEAD_DIR / "usage.db"
    if usage_path.exists():
        try:
            conn = sqlite3.connect(str(usage_path))
            conn.row_factory = sqlite3.Row
            today_start = time.time() - 86400
            row = conn.execute(
                "SELECT COUNT(*) as cnt, COALESCE(SUM(total_tokens), 0) as tokens, "
                "COALESCE(SUM(cost_usd), 0) as cost FROM usage_records WHERE started_at >= ?",
                (today_start,)
            ).fetchone()
            result["usage"] = {
                "records_24h": row["cnt"] if row else 0,
                "tokens_24h": row["tokens"] if row else 0,
                "cost_24h": row["cost"] if row else 0.0,
            }
            conn.close()
        except Exception:
            pass

    return result
