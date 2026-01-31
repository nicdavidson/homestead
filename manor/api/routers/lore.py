"""Lore file endpoints — read/write from the monorepo lore/ directory."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/lore", tags=["lore"])


def _lore_dir() -> Path:
    d = settings.lore_path
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(filename: str) -> Path:
    """Resolve filename and ensure it stays within the lore directory."""
    lore_dir = _lore_dir()
    # Prevent directory traversal
    resolved = (lore_dir / filename).resolve()
    if not str(resolved).startswith(str(lore_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return resolved


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class LoreBody(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
def list_lore():
    """List all lore files."""
    lore_dir = _lore_dir()
    results = []
    for p in sorted(lore_dir.glob("*.md")):
        stat = p.stat()
        results.append({
            "filename": p.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })
    return results


@router.get("/{filename}")
def get_lore(filename: str):
    """Read a lore file's content."""
    path = _safe_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Lore file '{filename}' not found")

    content = path.read_text(encoding="utf-8")
    stat = path.stat()
    return {
        "filename": path.name,
        "content": content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }


@router.put("/{filename}")
def update_lore(filename: str, body: LoreBody):
    """Create or update a lore file."""
    path = _safe_path(filename)
    path.write_text(body.content, encoding="utf-8")
    stat = path.stat()
    return {
        "filename": path.name,
        "content": body.content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }
