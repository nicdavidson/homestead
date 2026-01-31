"""Scratchpad file endpoints — read/write markdown notes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/scratchpad", tags=["scratchpad"])


def _scratchpad_dir() -> Path:
    d = settings.scratchpad_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(filename: str) -> Path:
    """Resolve filename and ensure it stays within the scratchpad directory."""
    base = _scratchpad_dir()
    resolved = (base / filename).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return resolved


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ScratchpadBody(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
def list_scratchpad():
    """List all scratchpad files."""
    base = _scratchpad_dir()
    results = []
    for p in sorted(base.glob("*.md")):
        stat = p.stat()
        results.append({
            "name": p.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        })
    return results


@router.get("/{filename}")
def get_scratchpad(filename: str):
    """Read a scratchpad file."""
    path = _safe_path(filename)
    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"Scratchpad file '{filename}' not found"
        )

    content = path.read_text(encoding="utf-8")
    stat = path.stat()
    return {
        "name": path.name,
        "content": content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }


@router.put("/{filename}")
def write_scratchpad(filename: str, body: ScratchpadBody):
    """Create or update a scratchpad file."""
    path = _safe_path(filename)
    path.write_text(body.content, encoding="utf-8")
    stat = path.stat()

    # Update Cronicle memory index
    from ..memory import get_memory_index
    try:
        get_memory_index().upsert_document("scratchpad", f"scratchpad/{filename}", body.content)
    except Exception:
        pass

    return {
        "name": path.name,
        "content": body.content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
    }


@router.delete("/{filename}")
def delete_scratchpad(filename: str):
    """Delete a scratchpad file."""
    path = _safe_path(filename)
    if not path.exists():
        raise HTTPException(
            status_code=404, detail=f"Scratchpad file '{filename}' not found"
        )
    path.unlink()

    # Remove from Cronicle memory index
    from ..memory import get_memory_index
    try:
        get_memory_index().remove_document(f"scratchpad/{filename}")
    except Exception:
        pass

    return {"deleted": True, "name": filename}
