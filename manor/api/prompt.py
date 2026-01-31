"""Assemble the system prompt for Claude when spawned from the chat endpoint."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import settings

logger = logging.getLogger(__name__)

# Lore files loaded explicitly (in order) before the catch-all pass.
_CORE_LORE_FILES = {"soul.md", "identity.md", "claude.md", "user.md", "agents.md"}

_MCP_SECTION = """\
# Available Tools (MCP)

You have access to homestead tools via MCP. These let you:
- Manage tasks (create, update, list, change status)
- Manage scheduled jobs (create, toggle, trigger)
- Read and write lore files (your identity and context)
- Read and write scratchpad notes (persistent memory)
- Propose code changes for human review (propose_code_change)
- Send messages via the outbox
- Check system health and usage stats

Use these tools proactively. When you want to change code, always use propose_code_change \
so the human can review before applying."""


def _read_file(path: Path) -> str | None:
    """Return file contents or *None* if unreadable."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        logger.warning("prompt: could not read %s — skipping", path)
        return None


def _parse_skill_frontmatter(text: str) -> tuple[str, str]:
    """Extract *name* and *description* from YAML frontmatter.

    Expects the file to start with ``---`` fences.  Falls back to the
    filename-derived name and an empty description.
    """
    name = ""
    description = ""
    if not text.startswith("---"):
        return name, description
    try:
        end = text.index("---", 3)
        frontmatter = text[3:end]
        for line in frontmatter.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip().strip("\"'")
            if key == "name":
                name = value
            elif key == "description":
                description = value
    except ValueError:
        pass
    return name, description


def _build_skills_section() -> str | None:
    """Scan skills_dir for *.md files and return a formatted listing."""
    skills_dir: Path = settings.skills_dir
    if not skills_dir.is_dir():
        return None

    entries: list[str] = []
    for md in sorted(skills_dir.glob("*.md")):
        content = _read_file(md)
        if content is None:
            continue
        name, description = _parse_skill_frontmatter(content)
        display_name = name or md.stem
        if description:
            entries.append(f"- **{display_name}**: {description}")
        else:
            entries.append(f"- **{display_name}**")

    if not entries:
        return None

    return "# Skills\n\n" + "\n".join(entries)


def _build_scratchpad_hint() -> str | None:
    """Note which scratchpad files are available."""
    scratchpad_dir: Path = settings.scratchpad_dir
    if not scratchpad_dir.is_dir():
        return None

    files = sorted(p.name for p in scratchpad_dir.iterdir() if p.is_file())
    if not files:
        return None

    listing = ", ".join(f"`{f}`" for f in files)
    return (
        "# Scratchpad\n\n"
        f"You have persistent scratchpad notes available: {listing}.\n"
        "Read or update them via the scratchpad MCP tools."
    )


def _collect_extra_lore() -> str | None:
    """Load any *.md files in lore/ not already consumed by the core steps."""
    lore_path: Path = settings.lore_path
    if not lore_path.is_dir():
        return None

    parts: list[str] = []
    for md in sorted(lore_path.glob("*.md")):
        if md.name in _CORE_LORE_FILES:
            continue
        content = _read_file(md)
        if content:
            parts.append(content)

    return "\n\n".join(parts) if parts else None


def assemble_system_prompt() -> str:
    """Build the full system prompt from lore, skills, scratchpad, and MCP info.

    Parts are joined with ``\\n\\n---\\n\\n``.  Returns an empty string when
    nothing could be assembled.
    """
    parts: list[str] = []
    lore_path: Path = settings.lore_path

    # 1. Soul
    soul = _read_file(lore_path / "soul.md")
    if soul:
        parts.append(soul)

    # 2. Identity
    identity = _read_file(lore_path / "identity.md")
    if identity:
        parts.append(identity)

    # 3. Behavior (Claude-specific directives)
    behavior = _read_file(lore_path / "claude.md")
    if behavior:
        parts.append(behavior)

    # 4. User context
    user_ctx = _read_file(lore_path / "user.md")
    if user_ctx:
        parts.append(user_ctx)

    # 5. Agents
    agents = _read_file(lore_path / "agents.md")
    if agents:
        parts.append(agents)

    # 4. Skills listing
    skills = _build_skills_section()
    if skills:
        parts.append(skills)

    # 5. Scratchpad hint
    scratchpad = _build_scratchpad_hint()
    if scratchpad:
        parts.append(scratchpad)

    # 6. MCP awareness
    parts.append(_MCP_SECTION)

    # 7. Extra lore files
    extra = _collect_extra_lore()
    if extra:
        parts.append(extra)

    if not parts:
        return ""

    return "\n\n---\n\n".join(parts)
