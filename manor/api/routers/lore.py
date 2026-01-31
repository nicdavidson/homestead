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


def _base_lore_dir() -> Path:
    d = settings.lore_path / "base"
    return d


@router.get("")
def list_lore():
    """List all lore files with layer info (user override vs base default)."""
    lore_dir = _lore_dir()
    base_dir = _base_lore_dir()
    seen: set[str] = set()
    results = []

    # User overrides first
    for p in sorted(lore_dir.glob("*.md")):
        seen.add(p.name)
        stat = p.stat()
        # Check if there's also a base version
        has_base = (base_dir / p.name).is_file() if base_dir.is_dir() else False
        results.append({
            "name": p.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "layer": "user",
            "has_base": has_base,
        })

    # Base defaults not overridden
    if base_dir.is_dir():
        for p in sorted(base_dir.glob("*.md")):
            if p.name in seen:
                continue
            stat = p.stat()
            results.append({
                "name": p.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "layer": "base",
                "has_base": True,
            })

    return results


@router.get("/{filename}")
def get_lore(filename: str):
    """Read a lore file's content, falling back to base if no user override."""
    path = _safe_path(filename)
    layer = "user"

    if not path.exists():
        # Fall back to base
        base_dir = _base_lore_dir()
        if base_dir.is_dir():
            base_path = base_dir / filename
            if base_path.is_file():
                path = base_path
                layer = "base"
            else:
                raise HTTPException(status_code=404, detail=f"Lore file '{filename}' not found")
        else:
            raise HTTPException(status_code=404, detail=f"Lore file '{filename}' not found")

    content = path.read_text(encoding="utf-8")
    stat = path.stat()
    return {
        "name": path.name,
        "content": content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "layer": layer,
    }


@router.put("/{filename}")
def update_lore(filename: str, body: LoreBody):
    """Create or update a lore file."""
    path = _safe_path(filename)
    path.write_text(body.content, encoding="utf-8")
    stat = path.stat()

    # Update Cronicle memory index
    from ..memory import get_memory_index
    try:
        get_memory_index().upsert_document("lore", f"lore/{filename}", body.content)
    except Exception:
        pass  # Non-critical — index catches up on next reindex

    return {
        "name": path.name,
        "content": body.content,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "layer": "user",
    }
