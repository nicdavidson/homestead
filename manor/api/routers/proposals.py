"""Proposals endpoints — AI-proposed code changes with human review."""

from __future__ import annotations

import difflib
import json
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/proposals", tags=["proposals"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)

VALID_STATUSES = {"pending", "approved", "rejected", "applied", "failed"}

# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS proposals (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL DEFAULT '',
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    diff            TEXT NOT NULL,
    file_paths_json TEXT NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      REAL NOT NULL,
    reviewed_at     REAL,
    applied_at      REAL,
    review_notes    TEXT DEFAULT ''
)
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals (status)",
    "CREATE INDEX IF NOT EXISTS idx_proposals_session ON proposals (session_id)",
    "CREATE INDEX IF NOT EXISTS idx_proposals_created ON proposals (created_at)",
]

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    db = settings.proposals_db
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
        "title": row["title"],
        "description": row["description"],
        "diff": row["diff"],
        "file_paths": json.loads(row["file_paths_json"]) if row["file_paths_json"] else [],
        "status": row["status"],
        "created_at": row["created_at"],
        "reviewed_at": row["reviewed_at"],
        "applied_at": row["applied_at"],
        "review_notes": row["review_notes"],
    }


def _fetch_proposal(conn: sqlite3.Connection, proposal_id: str) -> sqlite3.Row:
    """Fetch a single proposal row or raise 404."""
    row = conn.execute(
        "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return row


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateProposalBody(BaseModel):
    title: str
    description: str = ""
    file_path: str
    original_content: str
    new_content: str
    session_id: str = ""


class UpdateStatusBody(BaseModel):
    status: str
    review_notes: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
def create_proposal(body: CreateProposalBody):
    """Create a new proposal with a server-generated unified diff."""
    original_lines = body.original_content.splitlines(keepends=True)
    new_lines = body.new_content.splitlines(keepends=True)

    diff_text = "".join(
        difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{body.file_path}",
            tofile=f"b/{body.file_path}",
        )
    )

    if not diff_text:
        raise HTTPException(
            status_code=400,
            detail="No differences detected between original and new content",
        )

    proposal_id = str(uuid.uuid4())
    now = time.time()

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO proposals "
            "(id, session_id, title, description, diff, file_paths_json, "
            "status, created_at, review_notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                proposal_id,
                body.session_id,
                body.title,
                body.description,
                diff_text,
                json.dumps([body.file_path]),
                "pending",
                now,
                "",
            ),
        )
        conn.commit()

        row = _fetch_proposal(conn, proposal_id)
        return _row_to_dict(row)
    finally:
        conn.close()


@router.get("")
def list_proposals(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List proposals with optional status filter."""
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    conn = _get_conn()
    try:
        clauses: list[str] = []
        params: list[Any] = []

        if status:
            clauses.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM proposals {where}", params
        ).fetchone()
        total = count_row["cnt"] if count_row else 0

        rows = conn.execute(
            f"SELECT * FROM proposals {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

        return {"total": total, "proposals": [_row_to_dict(r) for r in rows]}
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return {"total": 0, "proposals": []}
        raise
    finally:
        conn.close()


@router.get("/{proposal_id}")
def get_proposal(proposal_id: str):
    """Get a single proposal with full diff."""
    conn = _get_conn()
    try:
        row = _fetch_proposal(conn, proposal_id)
        return _row_to_dict(row)
    finally:
        conn.close()


@router.patch("/{proposal_id}")
def update_proposal_status(proposal_id: str, body: UpdateStatusBody):
    """Approve or reject a pending proposal."""
    if body.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="Status must be 'approved' or 'rejected'",
        )

    conn = _get_conn()
    try:
        row = _fetch_proposal(conn, proposal_id)
        current_status = row["status"]

        if current_status != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot change status from '{current_status}' to '{body.status}'. "
                       f"Only pending proposals can be approved or rejected.",
            )

        now = time.time()
        conn.execute(
            "UPDATE proposals SET status = ?, reviewed_at = ?, review_notes = ? WHERE id = ?",
            (body.status, now, body.review_notes, proposal_id),
        )
        conn.commit()

        row = _fetch_proposal(conn, proposal_id)
        return _row_to_dict(row)
    finally:
        conn.close()


@router.post("/{proposal_id}/apply")
def apply_proposal(proposal_id: str):
    """Apply an approved proposal by running git apply and committing."""
    conn = _get_conn()
    try:
        row = _fetch_proposal(conn, proposal_id)
        current_status = row["status"]

        if current_status != "approved":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot apply proposal with status '{current_status}'. "
                       f"Only approved proposals can be applied.",
            )

        diff_text = row["diff"]
        title = row["title"]

        # Apply the diff using git apply
        try:
            apply_result = subprocess.run(
                ["git", "apply", "--check", "-"],
                input=diff_text,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                timeout=30,
            )
            if apply_result.returncode != 0:
                error_msg = apply_result.stderr.strip() or apply_result.stdout.strip()
                raise subprocess.CalledProcessError(
                    apply_result.returncode, "git apply --check", error_msg
                )

            # Dry-run passed — apply for real
            subprocess.run(
                ["git", "apply", "-"],
                input=diff_text,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                timeout=30,
                check=True,
            )

            # Stage all changed files and commit
            file_paths = json.loads(row["file_paths_json"]) if row["file_paths_json"] else []
            for fp in file_paths:
                subprocess.run(
                    ["git", "add", fp],
                    capture_output=True,
                    text=True,
                    cwd=REPO_ROOT,
                    timeout=10,
                )

            commit_msg = f"Applied proposal: {title}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                timeout=30,
                check=True,
            )

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            # Mark as failed and store the error
            error_detail = str(exc)
            if isinstance(exc, subprocess.CalledProcessError) and exc.output:
                error_detail = exc.output
            elif isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
                error_detail = exc.stderr

            now = time.time()
            existing_notes = row["review_notes"] or ""
            failure_notes = (
                f"{existing_notes}\n--- Apply failed at {time.ctime(now)} ---\n{error_detail}"
            ).strip()

            conn.execute(
                "UPDATE proposals SET status = ?, review_notes = ? WHERE id = ?",
                ("failed", failure_notes, proposal_id),
            )
            conn.commit()

            row = _fetch_proposal(conn, proposal_id)
            return _row_to_dict(row)

        # Success — mark as applied
        now = time.time()
        conn.execute(
            "UPDATE proposals SET status = ?, applied_at = ? WHERE id = ?",
            ("applied", now, proposal_id),
        )
        conn.commit()

        row = _fetch_proposal(conn, proposal_id)
        return _row_to_dict(row)
    finally:
        conn.close()


@router.delete("/{proposal_id}")
def delete_proposal(proposal_id: str):
    """Delete a proposal."""
    conn = _get_conn()
    try:
        row = _fetch_proposal(conn, proposal_id)
        conn.execute("DELETE FROM proposals WHERE id = ?", (proposal_id,))
        conn.commit()
        return {"deleted": True, "id": proposal_id}
    finally:
        conn.close()
