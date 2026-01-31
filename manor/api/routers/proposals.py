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
    original_content TEXT NOT NULL DEFAULT '',
    new_content     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      REAL NOT NULL,
    reviewed_at     REAL,
    applied_at      REAL,
    review_notes    TEXT DEFAULT ''
)
"""

_CREATE_FILES_TABLE = """\
CREATE TABLE IF NOT EXISTS proposal_files (
    id            TEXT PRIMARY KEY,
    proposal_id   TEXT NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    file_path     TEXT NOT NULL,
    original_content TEXT NOT NULL DEFAULT '',
    new_content   TEXT NOT NULL DEFAULT '',
    diff          TEXT NOT NULL DEFAULT '',
    sort_order    INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_FILES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_proposal_files_proposal ON proposal_files (proposal_id)",
]

_MIGRATE_COLUMNS = [
    "ALTER TABLE proposals ADD COLUMN original_content TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE proposals ADD COLUMN new_content TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE proposals ADD COLUMN pr_url TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE proposals ADD COLUMN commit_sha TEXT NOT NULL DEFAULT ''",
]

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
    conn.execute(_CREATE_FILES_TABLE)
    for idx in _CREATE_INDEXES + _CREATE_FILES_INDEXES:
        conn.execute(idx)
    # Migrate: add columns if missing (idempotent)
    for stmt in _MIGRATE_COLUMNS:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    return conn


def _row_to_dict(row: sqlite3.Row, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    d = {
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
    # New columns (may be absent in old rows)
    try:
        d["original_content"] = row["original_content"]
        d["new_content"] = row["new_content"]
    except (IndexError, KeyError):
        d["original_content"] = ""
        d["new_content"] = ""
    try:
        d["pr_url"] = row["pr_url"]
    except (IndexError, KeyError):
        d["pr_url"] = ""
    try:
        d["commit_sha"] = row["commit_sha"]
    except (IndexError, KeyError):
        d["commit_sha"] = ""

    # Per-file diffs from proposal_files table
    d["files"] = []
    if conn is not None:
        file_rows = conn.execute(
            "SELECT file_path, diff, sort_order FROM proposal_files "
            "WHERE proposal_id = ? ORDER BY sort_order",
            (row["id"],),
        ).fetchall()
        d["files"] = [{"file_path": fr["file_path"], "diff": fr["diff"]} for fr in file_rows]

    return d


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


class ProposalFile(BaseModel):
    file_path: str
    original_content: str
    new_content: str


class CreateProposalBody(BaseModel):
    title: str
    description: str = ""
    files: list[ProposalFile] = []        # multi-file
    file_path: str = ""                   # legacy single-file
    original_content: str = ""            # legacy
    new_content: str = ""                 # legacy
    session_id: str = ""


class UpdateStatusBody(BaseModel):
    status: str
    review_notes: str = ""


def _rollback_files(saved: dict[str, str | None]) -> None:
    """Restore files to their pre-apply state."""
    for fp, content in saved.items():
        abs_fp = Path(REPO_ROOT) / fp
        if content is None:
            abs_fp.unlink(missing_ok=True)
        else:
            abs_fp.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _resolve_file(file_path: str, original_content: str, new_content: str) -> tuple[str, str, str]:
    """Resolve a single file's original/new content and generate its diff.

    Returns (actual_original, full_new_content, diff_text).
    Raises HTTPException if a snippet can't be located in the actual file.
    """
    file_abs = Path(REPO_ROOT) / file_path
    actual_original = ""
    full_new = new_content

    if file_abs.is_file():
        actual_original = file_abs.read_text(encoding="utf-8")

        agent_original = original_content.strip()
        if agent_original and agent_original != actual_original.strip():
            # Snippet mode — find the snippet in the real file and replace it
            idx = actual_original.find(agent_original)
            if idx == -1:
                idx = actual_original.find(original_content)
            if idx >= 0:
                full_new = (
                    actual_original[:idx]
                    + new_content
                    + actual_original[idx + len(agent_original):]
                )
            else:
                # Snippet not found — refuse rather than replacing the entire file
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not locate the original_content snippet in {file_path}. "
                           f"The snippet ({len(agent_original)} chars) was not found in the "
                           f"actual file ({len(actual_original)} chars). "
                           f"Send the full file content or a snippet that exactly matches.",
                )
    else:
        actual_original = original_content

    # Safety: reject if the new content would shrink the file by more than 80%
    # (likely a snippet being applied as a full replacement)
    if actual_original and full_new:
        orig_len = len(actual_original)
        new_len = len(full_new)
        if orig_len > 500 and new_len < orig_len * 0.2:
            raise HTTPException(
                status_code=400,
                detail=f"Rejected: new content for {file_path} is {new_len} chars vs "
                       f"original {orig_len} chars ({new_len*100//orig_len}% of original). "
                       f"This looks like a snippet, not a full file replacement. "
                       f"Use original_content to specify the section to replace.",
            )

    original_lines = actual_original.splitlines(keepends=True)
    new_lines = full_new.splitlines(keepends=True)
    diff_text = "".join(
        difflib.unified_diff(
            original_lines, new_lines,
            fromfile=f"a/{file_path}", tofile=f"b/{file_path}",
        )
    )
    return actual_original, full_new, diff_text


@router.post("")
def create_proposal(body: CreateProposalBody):
    """Create a new proposal with server-generated unified diffs.

    Accepts either a `files` array (multi-file) or legacy single-file fields
    (`file_path`, `original_content`, `new_content`).
    """
    # Normalise to a list of files
    files = list(body.files)
    if not files and body.file_path:
        files = [ProposalFile(
            file_path=body.file_path,
            original_content=body.original_content,
            new_content=body.new_content,
        )]

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Resolve each file
    all_diffs: list[str] = []
    file_rows: list[tuple[str, str, str, str]] = []  # (file_path, original, new, diff)
    file_paths: list[str] = []

    for i, f in enumerate(files):
        actual_original, full_new, diff_text = _resolve_file(
            f.file_path, f.original_content, f.new_content,
        )
        if diff_text:
            all_diffs.append(diff_text)
            file_rows.append((f.file_path, actual_original, full_new, diff_text))
            file_paths.append(f.file_path)

    if not all_diffs:
        raise HTTPException(
            status_code=400,
            detail="No differences detected between original and new content",
        )

    combined_diff = "\n".join(all_diffs)
    proposal_id = str(uuid.uuid4())
    now = time.time()

    # For backwards compat, store first file's content in the parent row
    first_original = file_rows[0][1] if file_rows else ""
    first_new = file_rows[0][2] if file_rows else ""

    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO proposals "
            "(id, session_id, title, description, diff, file_paths_json, "
            "original_content, new_content, status, created_at, review_notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                proposal_id,
                body.session_id,
                body.title,
                body.description,
                combined_diff,
                json.dumps(file_paths),
                first_original,
                first_new,
                "pending",
                now,
                "",
            ),
        )

        # Insert per-file rows
        for i, (fp, orig, new, diff) in enumerate(file_rows):
            conn.execute(
                "INSERT INTO proposal_files "
                "(id, proposal_id, file_path, original_content, new_content, diff, sort_order) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), proposal_id, fp, orig, new, diff, i),
            )

                conn.commit()

        row = _fetch_proposal(conn, proposal_id)
        result = _row_to_dict(row, conn)
        
        # Send Telegram notification
        _send_telegram_notification(proposal_id, body.title, body.description, file_paths)
        
        return result
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

        return {"total": total, "proposals": [_row_to_dict(r, conn) for r in rows]}
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
        return _row_to_dict(row, conn)
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
        return _row_to_dict(row, conn)
    finally:
        conn.close()


def _git(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a git command in REPO_ROOT."""
    defaults = {"capture_output": True, "text": True, "cwd": REPO_ROOT, "timeout": 30}
    defaults.update(kwargs)
    return subprocess.run(["git"] + args, **defaults)


def _current_branch() -> str:
    result = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else "master"


@router.post("/{proposal_id}/apply")
def apply_proposal(proposal_id: str):
    """Apply an approved proposal, optionally on a dedicated branch with a PR."""
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

        title = row["title"]
        file_paths = json.loads(row["file_paths_json"]) if row["file_paths_json"] else []

        # Load per-file content from proposal_files table
        pf_rows = conn.execute(
            "SELECT file_path, new_content FROM proposal_files "
            "WHERE proposal_id = ? ORDER BY sort_order",
            (proposal_id,),
        ).fetchall()

        # Build a map of file_path -> new_content
        file_content_map: dict[str, str] = {}
        if pf_rows:
            for pf in pf_rows:
                file_content_map[pf["file_path"]] = pf["new_content"]
        else:
            # Legacy: single file stored on the parent row
            new_content = ""
            try:
                new_content = row["new_content"]
            except (IndexError, KeyError):
                pass
            if file_paths and new_content:
                file_content_map[file_paths[0]] = new_content

        proposal_branch = settings.proposal_branch  # e.g. "milo", or "" for current branch

        # Save originals for rollback
        saved_originals: dict[str, str | None] = {}
        for fp in file_paths:
            abs_fp = Path(REPO_ROOT) / fp
            if abs_fp.is_file():
                saved_originals[fp] = abs_fp.read_text(encoding="utf-8")
            else:
                saved_originals[fp] = None

        original_branch = _current_branch()
        switched_branch = False
        pr_url = ""

        try:
            # Switch to proposal branch if configured
            if proposal_branch:
                _git(["fetch", "origin", proposal_branch], timeout=30)

                check = _git(["rev-parse", "--verify", proposal_branch])
                if check.returncode != 0:
                    remote_check = _git(["rev-parse", "--verify", f"origin/{proposal_branch}"])
                    if remote_check.returncode == 0:
                        _git(["checkout", "-b", proposal_branch, f"origin/{proposal_branch}"], check=True)
                    else:
                        _git(["checkout", "-b", proposal_branch], check=True)
                else:
                    _git(["checkout", proposal_branch], check=True)
                    _git(["pull", "--ff-only", "origin", proposal_branch], timeout=30)

                switched_branch = True

            if file_content_map:
                # Direct file write for each file
                for fp, content in file_content_map.items():
                    file_abs = Path(REPO_ROOT) / fp
                    file_abs.parent.mkdir(parents=True, exist_ok=True)
                    file_abs.write_text(content, encoding="utf-8")
            else:
                # Fallback to git apply for legacy proposals
                diff_text = row["diff"]
                apply_result = _git(["apply", "--check", "-"], input=diff_text)
                if apply_result.returncode != 0:
                    error_msg = apply_result.stderr.strip() or apply_result.stdout.strip()
                    raise subprocess.CalledProcessError(
                        apply_result.returncode, "git apply --check", error_msg
                    )
                _git(["apply", "-"], input=diff_text, check=True)

            # Run test command (if configured) before committing
            test_cmd = settings.proposal_test_cmd
            if test_cmd:
                test_result = subprocess.run(
                    test_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=REPO_ROOT,
                    timeout=120,
                )
                if test_result.returncode != 0:
                    _rollback_files(saved_originals)
                    test_output = (
                        test_result.stderr.strip()
                        or test_result.stdout.strip()
                        or "exit code " + str(test_result.returncode)
                    )
                    raise subprocess.CalledProcessError(
                        test_result.returncode,
                        f"test: {test_cmd}",
                        test_output,
                    )

            # Stage and commit
            for fp in file_paths:
                _git(["add", fp], timeout=10)

            commit_msg = f"proposal: {title}"
            _git(["commit", "-m", commit_msg], check=True)

            # Capture commit SHA
            sha_result = _git(["rev-parse", "HEAD"])
            commit_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else ""

            # Push and create PR if using a dedicated branch
            if proposal_branch:
                push_result = _git(["push", "origin", proposal_branch], timeout=60)
                if push_result.returncode != 0:
                    raise subprocess.CalledProcessError(
                        push_result.returncode, "git push",
                        push_result.stderr.strip() or push_result.stdout.strip(),
                    )

                # Create PR via gh CLI
                pr_body = row["description"] or f"Automated proposal: {title}"
                pr_result = subprocess.run(
                    [
                        "gh", "pr", "create",
                        "--base", "master",
                        "--head", proposal_branch,
                        "--title", title,
                        "--body", pr_body,
                    ],
                    capture_output=True,
                    text=True,
                    cwd=REPO_ROOT,
                    timeout=30,
                )
                if pr_result.returncode == 0:
                    pr_url = pr_result.stdout.strip()
                else:
                    # PR creation failed — might already exist. Try to find existing.
                    list_result = subprocess.run(
                        ["gh", "pr", "list", "--head", proposal_branch, "--json", "url", "--limit", "1"],
                        capture_output=True,
                        text=True,
                        cwd=REPO_ROOT,
                        timeout=15,
                    )
                    if list_result.returncode == 0:
                        try:
                            prs = json.loads(list_result.stdout)
                            if prs:
                                pr_url = prs[0]["url"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            # Rollback on any failure
            _rollback_files(saved_originals)

            error_detail = str(exc)
            if isinstance(exc, subprocess.CalledProcessError):
                error_detail = exc.stderr or exc.output or str(exc)

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

            # Switch back to original branch
            if switched_branch:
                _git(["checkout", original_branch])

            row = _fetch_proposal(conn, proposal_id)
            return _row_to_dict(row, conn)

        # Switch back to original branch
        if switched_branch:
            _git(["checkout", original_branch])

        # Success — mark as applied
        now = time.time()
        conn.execute(
            "UPDATE proposals SET status = ?, applied_at = ?, pr_url = ?, commit_sha = ? WHERE id = ?",
            ("applied", now, pr_url, commit_sha, proposal_id),
        )
        conn.commit()

        row = _fetch_proposal(conn, proposal_id)
        return _row_to_dict(row, conn)
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
