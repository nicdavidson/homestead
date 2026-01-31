"""Task store backed by SQLite.

Database lives at ~/.homestead/steward/tasks.db and uses WAL mode with a
busy_timeout of 5 000 ms — consistent with every other Homestead package.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from steward.models import (
    Blocker,
    BlockerType,
    Task,
    TaskPriority,
    TaskStatus,
)

_DEFAULT_DB = Path("~/.homestead/steward/tasks.db").expanduser()

_CREATE_TASKS = """\
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT NOT NULL DEFAULT 'normal',
    assignee TEXT DEFAULT 'auto',
    blockers_json TEXT DEFAULT '[]',
    depends_on_json TEXT DEFAULT '[]',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    tags_json TEXT DEFAULT '[]',
    notes_json TEXT DEFAULT '[]',
    source TEXT DEFAULT ''
)
"""

_CREATE_IDX_STATUS = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status)"
)
_CREATE_IDX_PRIORITY = (
    "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority, status)"
)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _blocker_to_dict(b: Blocker) -> dict:
    return {
        "type": b.type.value,
        "description": b.description,
        "created_at": b.created_at,
        "resolved_at": b.resolved_at,
        "resolved_by": b.resolved_by,
        "resolution": b.resolution,
    }


def _dict_to_blocker(d: dict) -> Blocker:
    return Blocker(
        type=BlockerType(d["type"]),
        description=d["description"],
        created_at=d.get("created_at", 0.0),
        resolved_at=d.get("resolved_at"),
        resolved_by=d.get("resolved_by"),
        resolution=d.get("resolution"),
    )


def _row_to_task(row: sqlite3.Row) -> Task:
    blockers_raw = json.loads(row["blockers_json"] or "[]")
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"] or "",
        status=TaskStatus(row["status"]),
        priority=TaskPriority(row["priority"]),
        assignee=row["assignee"] or "auto",
        blockers=[_dict_to_blocker(b) for b in blockers_raw],
        depends_on=json.loads(row["depends_on_json"] or "[]"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
        tags=json.loads(row["tags_json"] or "[]"),
        notes=json.loads(row["notes_json"] or "[]"),
        source=row["source"] or "",
    )


# ---------------------------------------------------------------------------
# TaskStore
# ---------------------------------------------------------------------------

class TaskStore:
    """SQLite-backed task store."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # -- connection ---------------------------------------------------------

    def _connect(self, readonly: bool = False) -> sqlite3.Connection:
        uri = f"file:{self._db_path}"
        if readonly:
            uri += "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(_CREATE_TASKS)
            conn.execute(_CREATE_IDX_STATUS)
            conn.execute(_CREATE_IDX_PRIORITY)
            conn.commit()
        finally:
            conn.close()

    # -- public API ---------------------------------------------------------

    def save(self, task: Task) -> None:
        """Insert or replace a task."""
        conn = self._connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO tasks "
                "(id, title, description, status, priority, assignee, "
                "blockers_json, depends_on_json, created_at, updated_at, "
                "completed_at, tags_json, notes_json, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task.id,
                    task.title,
                    task.description,
                    task.status.value,
                    task.priority.value,
                    task.assignee,
                    json.dumps([_blocker_to_dict(b) for b in task.blockers]),
                    json.dumps(task.depends_on),
                    task.created_at,
                    task.updated_at,
                    task.completed_at,
                    json.dumps(task.tags),
                    json.dumps(task.notes),
                    task.source,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, task_id: str) -> Task | None:
        """Fetch a single task by ID, or None if not found."""
        conn = self._connect(readonly=True)
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None
            return _row_to_task(row)
        finally:
            conn.close()

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        assignee: str | None = None,
        tag: str | None = None,
    ) -> list[Task]:
        """List tasks with optional filters."""
        clauses: list[str] = []
        params: list[object] = []

        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if assignee is not None:
            clauses.append("assignee = ?")
            params.append(assignee)
        if tag is not None:
            # tags are stored as a JSON array — use LIKE for a simple match
            clauses.append("tags_json LIKE ?")
            params.append(f'%"{tag}"%')

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"SELECT * FROM tasks{where} ORDER BY created_at DESC"

        conn = self._connect(readonly=True)
        try:
            rows = conn.execute(query, params).fetchall()
            return [_row_to_task(r) for r in rows]
        finally:
            conn.close()

    def delete(self, task_id: str) -> bool:
        """Delete a task. Returns True if a row was actually removed."""
        conn = self._connect()
        try:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def update_status(self, task_id: str, new_status: TaskStatus) -> Task | None:
        """Quick status change. Sets completed_at when moving to COMPLETED."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None

            now = time.time()
            completed_at = now if new_status == TaskStatus.COMPLETED else row["completed_at"]

            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ?, completed_at = ? "
                "WHERE id = ?",
                (new_status.value, now, completed_at, task_id),
            )
            conn.commit()

            task = _row_to_task(row)
            task.status = new_status
            task.updated_at = now
            task.completed_at = completed_at
            return task
        finally:
            conn.close()

    def add_note(self, task_id: str, note: str) -> Task | None:
        """Append a note to a task."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None

            notes = json.loads(row["notes_json"] or "[]")
            notes.append(note)
            now = time.time()

            conn.execute(
                "UPDATE tasks SET notes_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(notes), now, task_id),
            )
            conn.commit()

            task = _row_to_task(row)
            task.notes = notes
            task.updated_at = now
            return task
        finally:
            conn.close()

    def add_blocker(self, task_id: str, blocker: Blocker) -> Task | None:
        """Add a blocker to a task."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None

            blockers = json.loads(row["blockers_json"] or "[]")
            blockers.append(_blocker_to_dict(blocker))
            now = time.time()

            conn.execute(
                "UPDATE tasks SET blockers_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(blockers), now, task_id),
            )
            conn.commit()

            task = _row_to_task(row)
            task.blockers = [_dict_to_blocker(b) for b in blockers]
            task.updated_at = now
            return task
        finally:
            conn.close()

    def resolve_blocker(
        self,
        task_id: str,
        blocker_index: int,
        resolved_by: str,
        resolution: str,
    ) -> Task | None:
        """Mark a specific blocker (by index) as resolved."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None

            blockers = json.loads(row["blockers_json"] or "[]")
            if blocker_index < 0 or blocker_index >= len(blockers):
                return None

            now = time.time()
            blockers[blocker_index]["resolved_at"] = now
            blockers[blocker_index]["resolved_by"] = resolved_by
            blockers[blocker_index]["resolution"] = resolution

            conn.execute(
                "UPDATE tasks SET blockers_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(blockers), now, task_id),
            )
            conn.commit()

            task = _row_to_task(row)
            task.blockers = [_dict_to_blocker(b) for b in blockers]
            task.updated_at = now
            return task
        finally:
            conn.close()

    def summary(self) -> dict:
        """Return a dict of {status_value: count}."""
        conn = self._connect(readonly=True)
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
            ).fetchall()
            result = {s.value: 0 for s in TaskStatus}
            for row in rows:
                result[row["status"]] = row["cnt"]
            result["total"] = sum(result.values())
            return result
        finally:
            conn.close()
