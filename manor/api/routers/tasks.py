"""Task management endpoints.

Reads and writes directly to the Steward tasks.db SQLite database.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# ---------------------------------------------------------------------------
# DB path & schema
# ---------------------------------------------------------------------------

_DB_PATH = Path("~/.homestead/steward/tasks.db").expanduser()

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
# DB helpers
# ---------------------------------------------------------------------------


def _get_conn(readonly: bool = False) -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TASKS)
    conn.execute(_CREATE_IDX_STATUS)
    conn.execute(_CREATE_IDX_PRIORITY)
    conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"] or "",
        "status": row["status"],
        "priority": row["priority"],
        "assignee": row["assignee"] or "auto",
        "blockers": json.loads(row["blockers_json"] or "[]"),
        "depends_on": json.loads(row["depends_on_json"] or "[]"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "completed_at": row["completed_at"],
        "tags": json.loads(row["tags_json"] or "[]"),
        "notes": json.loads(row["notes_json"] or "[]"),
        "source": row["source"] or "",
    }


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

_VALID_STATUSES = {"pending", "in_progress", "blocked", "completed", "cancelled"}
_VALID_PRIORITIES = {"low", "normal", "high", "urgent"}


class CreateTaskBody(BaseModel):
    title: str
    description: str = ""
    status: str = "pending"
    priority: str = "normal"
    assignee: str = "auto"
    depends_on: list[str] = []
    tags: list[str] = []
    notes: list[str] = []
    source: str = ""


class UpdateTaskBody(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee: str | None = None
    depends_on: list[str] | None = None
    tags: list[str] | None = None
    notes: list[str] | None = None
    source: str | None = None


class ChangeStatusBody(BaseModel):
    status: str


class AddNoteBody(BaseModel):
    note: str


class AddBlockerBody(BaseModel):
    type: str
    description: str


class ResolveBlockerBody(BaseModel):
    resolved_by: str
    resolution: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/summary")
def task_summary():
    """Return task counts grouped by status."""
    conn = _get_conn(readonly=True)
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
        ).fetchall()
        result = {s: 0 for s in _VALID_STATUSES}
        for row in rows:
            result[row["status"]] = row["cnt"]
        result["total"] = sum(result.values())
        return result
    finally:
        conn.close()


@router.get("")
def list_tasks(
    status: str | None = Query(None),
    assignee: str | None = Query(None),
    tag: str | None = Query(None),
):
    """List tasks with optional filters."""
    clauses: list[str] = []
    params: list[object] = []

    if status is not None:
        if status not in _VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        clauses.append("status = ?")
        params.append(status)
    if assignee is not None:
        clauses.append("assignee = ?")
        params.append(assignee)
    if tag is not None:
        clauses.append("tags_json LIKE ?")
        params.append(f'%"{tag}"%')

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"SELECT * FROM tasks{where} ORDER BY created_at DESC"

    conn = _get_conn(readonly=True)
    try:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{task_id}")
def get_task(task_id: str):
    """Get a single task by ID."""
    conn = _get_conn(readonly=True)
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return _row_to_dict(row)
    finally:
        conn.close()


@router.post("", status_code=201)
def create_task(body: CreateTaskBody):
    """Create a new task."""
    if body.status not in _VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
    if body.priority not in _VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority: {body.priority}")

    now = time.time()
    task_id = str(uuid.uuid4())

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO tasks "
            "(id, title, description, status, priority, assignee, "
            "blockers_json, depends_on_json, created_at, updated_at, "
            "completed_at, tags_json, notes_json, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task_id,
                body.title,
                body.description,
                body.status,
                body.priority,
                body.assignee,
                "[]",
                json.dumps(body.depends_on),
                now,
                now,
                now if body.status == "completed" else None,
                json.dumps(body.tags),
                json.dumps(body.notes),
                body.source,
            ),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


@router.put("/{task_id}")
def update_task(task_id: str, body: UpdateTaskBody):
    """Update an existing task (partial update)."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        sets: list[str] = []
        params: list[object] = []

        if body.title is not None:
            sets.append("title = ?")
            params.append(body.title)
        if body.description is not None:
            sets.append("description = ?")
            params.append(body.description)
        if body.status is not None:
            if body.status not in _VALID_STATUSES:
                raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
            sets.append("status = ?")
            params.append(body.status)
            if body.status == "completed":
                sets.append("completed_at = ?")
                params.append(time.time())
        if body.priority is not None:
            if body.priority not in _VALID_PRIORITIES:
                raise HTTPException(status_code=400, detail=f"Invalid priority: {body.priority}")
            sets.append("priority = ?")
            params.append(body.priority)
        if body.assignee is not None:
            sets.append("assignee = ?")
            params.append(body.assignee)
        if body.depends_on is not None:
            sets.append("depends_on_json = ?")
            params.append(json.dumps(body.depends_on))
        if body.tags is not None:
            sets.append("tags_json = ?")
            params.append(json.dumps(body.tags))
        if body.notes is not None:
            sets.append("notes_json = ?")
            params.append(json.dumps(body.notes))
        if body.source is not None:
            sets.append("source = ?")
            params.append(body.source)

        if not sets:
            return _row_to_dict(row)

        now = time.time()
        sets.append("updated_at = ?")
        params.append(now)
        params.append(task_id)

        conn.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", params
        )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


@router.put("/{task_id}/status")
def change_status(task_id: str, body: ChangeStatusBody):
    """Quick status change for a task."""
    if body.status not in _VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        now = time.time()
        completed_at = now if body.status == "completed" else row["completed_at"]

        conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ?, completed_at = ? "
            "WHERE id = ?",
            (body.status, now, completed_at, task_id),
        )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


@router.post("/{task_id}/notes")
def add_note(task_id: str, body: AddNoteBody):
    """Append a note to a task."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        notes = json.loads(row["notes_json"] or "[]")
        notes.append(body.note)
        now = time.time()

        conn.execute(
            "UPDATE tasks SET notes_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(notes), now, task_id),
        )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


@router.post("/{task_id}/blockers")
def add_blocker(task_id: str, body: AddBlockerBody):
    """Add a blocker to a task."""
    valid_blocker_types = {"human_input", "human_approval", "human_action", "dependency"}
    if body.type not in valid_blocker_types:
        raise HTTPException(status_code=400, detail=f"Invalid blocker type: {body.type}")

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        blockers = json.loads(row["blockers_json"] or "[]")
        blockers.append({
            "type": body.type,
            "description": body.description,
            "created_at": time.time(),
            "resolved_at": None,
            "resolved_by": None,
            "resolution": None,
        })
        now = time.time()

        conn.execute(
            "UPDATE tasks SET blockers_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(blockers), now, task_id),
        )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


@router.put("/{task_id}/blockers/{index}/resolve")
def resolve_blocker(task_id: str, index: int, body: ResolveBlockerBody):
    """Resolve a specific blocker by index."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        blockers = json.loads(row["blockers_json"] or "[]")
        if index < 0 or index >= len(blockers):
            raise HTTPException(status_code=404, detail="Blocker index out of range")

        now = time.time()
        blockers[index]["resolved_at"] = now
        blockers[index]["resolved_by"] = body.resolved_by
        blockers[index]["resolution"] = body.resolution

        conn.execute(
            "UPDATE tasks SET blockers_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(blockers), now, task_id),
        )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


@router.delete("/{task_id}")
def delete_task(task_id: str):
    """Delete a task."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return {"deleted": True, "id": task_id}
    finally:
        conn.close()
