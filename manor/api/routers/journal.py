"""Journal endpoints — AI reflections and session notes."""
from __future__ import annotations

import time
from datetime import date as dt_date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..memory import get_memory_index

router = APIRouter(prefix="/api/journal", tags=["journal"])


def _journal_dir() -> Path:
    d = settings.journal_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(date_str: str) -> Path:
    """Validate date format and return safe path."""
    # Validate YYYY-MM-DD format
    try:
        dt_date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    base = _journal_dir()
    filename = f"{date_str}.md"
    resolved = (base / filename).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid date")
    return resolved


class JournalBody(BaseModel):
    content: str


class JournalAppendBody(BaseModel):
    content: str


@router.get("")
def list_journal():
    """List all journal entries."""
    base = _journal_dir()
    results = []
    for p in sorted(base.glob("*.md"), reverse=True):
        stat = p.stat()
        results.append({
            "date": p.stem,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })
    return results


@router.get("/{date}")
def get_journal(date: str):
    """Read a journal entry by date."""
    path = _safe_path(date)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No journal entry for {date}")

    content = path.read_text(encoding="utf-8")
    stat = path.stat()
    return {
        "date": date,
        "content": content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }


@router.put("/{date}")
def write_journal(date: str, body: JournalBody):
    """Write or replace a journal entry."""
    path = _safe_path(date)
    path.write_text(body.content, encoding="utf-8")
    stat = path.stat()

    # Update memory index
    idx = get_memory_index()
    idx.upsert_document("journal", f"journal/{date}.md", body.content, title=date)

    return {
        "date": date,
        "content": body.content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }


@router.post("/append")
def append_journal(body: JournalAppendBody):
    """Append to today's journal entry."""
    today = dt_date.today().isoformat()
    path = _safe_path(today)

    # Read existing content
    existing = ""
    if path.exists():
        existing = path.read_text(encoding="utf-8")

    # Append with timestamp
    timestamp = time.strftime("%H:%M")
    entry = f"\n\n## {timestamp}\n\n{body.content}" if existing else f"# Journal — {today}\n\n## {timestamp}\n\n{body.content}"
    new_content = existing + entry

    path.write_text(new_content, encoding="utf-8")
    stat = path.stat()

    # Update memory index
    idx = get_memory_index()
    idx.upsert_document("journal", f"journal/{today}.md", new_content, title=today)

    return {
        "date": today,
        "content": new_content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }
