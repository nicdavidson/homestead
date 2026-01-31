"""Session management endpoints.

Reads and writes directly to the Herald sessions.db SQLite database.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS sessions (
    chat_id           INTEGER NOT NULL,
    name              TEXT    NOT NULL,
    user_id           INTEGER NOT NULL,
    claude_session_id TEXT    NOT NULL,
    model             TEXT    NOT NULL DEFAULT 'claude',
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        REAL    NOT NULL,
    last_active_at    REAL    NOT NULL,
    message_count     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, name)
)
"""


def _get_conn(readonly: bool = False) -> sqlite3.Connection:
    db_path = settings.sessions_db
    db_path.parent.mkdir(parents=True, exist_ok=True)
    uri = f"file:{db_path}"
    if readonly:
        uri += "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    if not readonly:
        conn.execute(_CREATE_TABLE)
        conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "chat_id": row["chat_id"],
        "name": row["name"],
        "user_id": row["user_id"],
        "claude_session_id": row["claude_session_id"],
        "model": row["model"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "last_active_at": row["last_active_at"],
        "message_count": row["message_count"],
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateSessionBody(BaseModel):
    chat_id: int
    name: str = "default"
    model: str = "claude"
    user_id: int = 0


class ChangeModelBody(BaseModel):
    model: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
def list_all_sessions():
    """List all sessions across all chats."""
    conn = _get_conn(readonly=True)
    try:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY last_active_at DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{chat_id}")
def list_sessions_for_chat(chat_id: int):
    """List sessions for a specific chat."""
    conn = _get_conn(readonly=True)
    try:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE chat_id = ? ORDER BY last_active_at DESC",
            (chat_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


@router.post("", status_code=201)
def create_session(body: CreateSessionBody):
    """Create a new session (and set it as active for the chat)."""
    conn = _get_conn()
    try:
        now = time.time()
        session_id = str(uuid.uuid4())

        # Check if session already exists
        existing = conn.execute(
            "SELECT 1 FROM sessions WHERE chat_id = ? AND name = ?",
            (body.chat_id, body.name),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Session '{body.name}' already exists for chat {body.chat_id}",
            )

        conn.execute(
            "INSERT INTO sessions "
            "(chat_id, name, user_id, claude_session_id, model, is_active, "
            "created_at, last_active_at, message_count) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?, 0)",
            (body.chat_id, body.name, body.user_id, session_id, body.model, now, now),
        )

        # Deactivate other sessions for this chat
        conn.execute(
            "UPDATE sessions SET is_active = 0 WHERE chat_id = ? AND name != ?",
            (body.chat_id, body.name),
        )
        conn.commit()

        return {
            "chat_id": body.chat_id,
            "name": body.name,
            "user_id": body.user_id,
            "claude_session_id": session_id,
            "model": body.model,
            "is_active": True,
            "created_at": now,
            "last_active_at": now,
            "message_count": 0,
        }
    finally:
        conn.close()


@router.put("/{chat_id}/{name}/activate")
def activate_session(chat_id: int, name: str):
    """Switch the active session for a chat."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE chat_id = ? AND name = ?",
            (chat_id, name),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")

        conn.execute(
            "UPDATE sessions SET is_active = 0 WHERE chat_id = ?", (chat_id,)
        )
        conn.execute(
            "UPDATE sessions SET is_active = 1 WHERE chat_id = ? AND name = ?",
            (chat_id, name),
        )
        conn.commit()
        result = _row_to_dict(row)
        result["is_active"] = True
        return result
    finally:
        conn.close()


@router.put("/{chat_id}/{name}/model")
def change_model(chat_id: int, name: str, body: ChangeModelBody):
    """Change the model for a session."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE chat_id = ? AND name = ?",
            (chat_id, name),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")

        conn.execute(
            "UPDATE sessions SET model = ? WHERE chat_id = ? AND name = ?",
            (body.model, chat_id, name),
        )
        conn.commit()
        result = _row_to_dict(row)
        result["model"] = body.model
        return result
    finally:
        conn.close()


@router.delete("/{chat_id}/{name}")
def delete_session(chat_id: int, name: str):
    """Delete a session."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE chat_id = ? AND name = ?",
            (chat_id, name),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")

        conn.execute(
            "DELETE FROM sessions WHERE chat_id = ? AND name = ?",
            (chat_id, name),
        )
        conn.commit()
        return {"deleted": True, "chat_id": chat_id, "name": name}
    finally:
        conn.close()
