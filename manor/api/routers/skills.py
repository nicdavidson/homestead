"""Skill management endpoints — YAML-front-matter markdown files."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/skills", tags=["skills"])


# ---------------------------------------------------------------------------
# Skill parsing (self-contained, mirrors common.skills logic)
# ---------------------------------------------------------------------------


def _parse_skill(path: Path) -> dict | None:
    """Parse a skill markdown file with YAML front-matter."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not text.startswith("---"):
        return {
            "name": path.stem,
            "description": "",
            "content": text,
            "tags": [],
            "filename": path.name,
        }

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {
            "name": path.stem,
            "description": "",
            "content": text,
            "tags": [],
            "filename": path.name,
        }

    header = parts[1].strip()
    body = parts[2].strip()

    meta: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()

    return {
        "name": meta.get("name", path.stem),
        "description": meta.get("description", ""),
        "content": body,
        "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
        "filename": path.name,
    }


def _skills_dir() -> Path:
    d = settings.skills_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class SkillBody(BaseModel):
    description: str = ""
    content: str
    tags: list[str] = []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("")
def list_skills():
    """List all skills (name, description, tags)."""
    skills_dir = _skills_dir()
    results = []
    for p in sorted(skills_dir.glob("*.md")):
        skill = _parse_skill(p)
        if skill:
            # Return summary (without full content)
            results.append({
                "name": skill["name"],
                "description": skill["description"],
                "tags": skill["tags"],
                "filename": skill["filename"],
            })
    return results


@router.get("/{name}")
def get_skill(name: str):
    """Get full skill content by name."""
    skills_dir = _skills_dir()

    # Try exact filename match first
    path = skills_dir / f"{name}.md"
    if path.exists():
        skill = _parse_skill(path)
        if skill:
            return skill

    # Fall back to searching by name field in front-matter
    for p in skills_dir.glob("*.md"):
        skill = _parse_skill(p)
        if skill and skill["name"] == name:
            return skill

    raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")


@router.put("/{name}")
def save_skill(name: str, body: SkillBody):
    """Create or update a skill file."""
    skills_dir = _skills_dir()
    filename = name.replace(" ", "-").lower() + ".md"
    path = skills_dir / filename

    tags_str = ", ".join(body.tags)
    header = (
        f"---\nname: {name}\n"
        f"description: {body.description}\n"
        f"tags: {tags_str}\n---\n\n"
    )
    path.write_text(header + body.content, encoding="utf-8")

    return {
        "name": name,
        "description": body.description,
        "content": body.content,
        "tags": body.tags,
        "filename": filename,
    }


@router.delete("/{name}")
def delete_skill(name: str):
    """Delete a skill file."""
    skills_dir = _skills_dir()

    # Try exact filename match
    path = skills_dir / f"{name}.md"
    if path.exists():
        path.unlink()
        return {"deleted": True, "name": name}

    # Fall back to searching by name
    for p in skills_dir.glob("*.md"):
        skill = _parse_skill(p)
        if skill and skill["name"] == name:
            p.unlink()
            return {"deleted": True, "name": name}

    raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
