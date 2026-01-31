from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    content: str
    tags: list[str]
    path: Path


class SkillManager:
    """Markdown-file-based skill library.

    Skills are stored as ``*.md`` files under *skills_dir*.  Each file has
    a YAML-ish front-matter header:

        ---
        name: git-rebase
        description: Interactive git rebase workflow
        tags: git, workflow
        ---

        Body of the skill...
    """

    def __init__(self, skills_dir: str | Path = "~/.homestead/skills") -> None:
        self._dir = Path(skills_dir).expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)

    def list_skills(self) -> list[Skill]:
        skills: list[Skill] = []
        for p in sorted(self._dir.glob("*.md")):
            skill = self._parse(p)
            if skill:
                skills.append(skill)
        return skills

    def get(self, name: str) -> Skill | None:
        for p in self._dir.glob("*.md"):
            skill = self._parse(p)
            if skill and skill.name == name:
                return skill
        return None

    def save(self, name: str, description: str, content: str, tags: list[str] | None = None) -> Skill:
        tags = tags or []
        filename = name.replace(" ", "-").lower() + ".md"
        path = self._dir / filename
        header = (
            f"---\nname: {name}\n"
            f"description: {description}\n"
            f"tags: {', '.join(tags)}\n---\n\n"
        )
        path.write_text(header + content, encoding="utf-8")
        return Skill(name=name, description=description, content=content, tags=tags, path=path)

    def search(self, query: str) -> list[Skill]:
        query_lower = query.lower()
        results = []
        for skill in self.list_skills():
            if (
                query_lower in skill.name.lower()
                or query_lower in skill.description.lower()
                or any(query_lower in t.lower() for t in skill.tags)
            ):
                results.append(skill)
        return results

    # -- internal --------------------------------------------------------------

    @staticmethod
    def _parse(path: Path) -> Skill | None:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return None

        if not text.startswith("---"):
            return Skill(name=path.stem, description="", content=text, tags=[], path=path)

        parts = text.split("---", 2)
        if len(parts) < 3:
            return Skill(name=path.stem, description="", content=text, tags=[], path=path)

        header = parts[1].strip()
        body = parts[2].strip()

        meta: dict[str, str] = {}
        for line in header.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()

        return Skill(
            name=meta.get("name", path.stem),
            description=meta.get("description", ""),
            content=body,
            tags=[t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
            path=path,
        )
