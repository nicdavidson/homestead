from __future__ import annotations

import logging
from pathlib import Path

from herald.config import Config

log = logging.getLogger(__name__)


def assemble_system_prompt(config: Config) -> str:
    """Build the full system prompt from lore files, skills, and scratchpad context.

    Reads files lazily at call time so the prompt reflects current state.
    """
    parts: list[str] = []

    # 1. Soul — core identity
    soul = _read_lore(config, "soul.md")
    if soul:
        parts.append(soul)

    # 2. Identity
    identity = _read_lore(config, "identity.md")
    if identity:
        parts.append(identity)

    # 3. Behavior directives (claude.md)
    behavior = _read_lore(config, "claude.md")
    if behavior:
        parts.append(behavior)

    # 4. User context
    user = _read_lore(config, "user.md")
    if user:
        parts.append(user)
    else:
        parts.append(
            "# User\n\n"
            "**No user.md found.** Ask the user to tell you about themselves "
            "so you can create lore/user.md for future sessions. Offer to write "
            "it for them using the `write_lore` MCP tool."
        )

    # 5. Agents
    agents = _read_lore(config, "agents.md")
    if agents:
        parts.append(agents)

    # 6. Available skills (lazy-loaded, just names + descriptions)
    skills_section = _build_skills_section(config)
    if skills_section:
        parts.append(skills_section)

    # 5. Scratchpad hint — remind the agent about its memory
    scratchpad_dir = Path(config.homestead_data_dir).expanduser() / "scratchpad"
    if scratchpad_dir.is_dir():
        files = sorted(scratchpad_dir.glob("*.md"))
        if files:
            names = [f.stem for f in files[:10]]
            parts.append(
                f"# Scratchpad\n\n"
                f"Your scratchpad at `{scratchpad_dir}` has {len(files)} note(s): "
                f"{', '.join(names)}. Read them when relevant."
            )
        else:
            parts.append(
                f"# Scratchpad\n\n"
                f"Your scratchpad at `{scratchpad_dir}` is empty. "
                f"Use it to store notes, plans, and context that should persist across sessions."
            )

    # 6. Any extra lore files (*.md in lore/ not already loaded)
    _loaded = {"soul.md", "identity.md", "claude.md", "user.md", "agents.md"}
    if config.lore_dir:
        lore_path = Path(config.lore_dir)
        for f in sorted(lore_path.glob("*.md")):
            if f.name not in _loaded:
                content = f.read_text(encoding="utf-8").strip()
                if content:
                    parts.append(content)

    # 7. MCP tools awareness — remind the agent what it can do via homestead
    if config.mcp_config_path:
        parts.append(_MCP_SECTION)

    if not parts:
        # Fallback to .env system prompt
        return config.system_prompt

    return "\n\n---\n\n".join(parts)


_MCP_SECTION = """\
# Homestead MCP Tools

You have access to MCP tools that connect you to the homestead infrastructure. \
Use them proactively — don't just talk about what you could do, actually do it.

## Available tools

- **Tasks**: `list_tasks`, `create_task`, `update_task`, `update_task_status`, `add_task_note`, `delete_task`, `task_summary` — manage your work queue
- **Jobs**: `list_jobs`, `create_job`, `update_job`, `toggle_job`, `trigger_job`, `delete_job`, `job_summary` — manage scheduled/cron jobs
- **Lore**: `list_lore`, `read_lore`, `write_lore` — read and update your identity/context files
- **Skills**: `list_skills`, `read_skill`, `write_skill`, `delete_skill` — manage reusable skill documents
- **Scratchpad**: `list_scratchpad`, `read_scratchpad`, `write_scratchpad`, `delete_scratchpad` — persistent notes/memory
- **Proposals**: `propose_code_change` — propose code changes for human review (don't modify code directly)
- **Outbox**: `send_message` — send messages to Telegram chats
- **Health**: `check_health` — check system health
- **Usage**: `query_usage` — check API usage stats

## Important

- For code changes to the homestead codebase, use `propose_code_change` instead of editing files directly. This creates a reviewable proposal.
- Use tasks to track your work. Create tasks for things you need to do, update status as you go.
- Write to scratchpad to remember things across sessions.
- Check your scratchpad and tasks at the start of conversations for context on ongoing work.
"""


def _read_lore(config: Config, filename: str) -> str | None:
    if not config.lore_dir:
        return None
    path = Path(config.lore_dir) / filename
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        return content if content else None
    except OSError:
        log.debug("Failed to read lore file: %s", path)
        return None


def _build_skills_section(config: Config) -> str | None:
    skills_dir = Path(config.homestead_data_dir).expanduser() / "skills"
    if not skills_dir.is_dir():
        return None

    skills: list[tuple[str, str]] = []
    for p in sorted(skills_dir.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
            name = p.stem
            desc = ""
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().splitlines():
                        if line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip()
                        elif line.startswith("name:"):
                            name = line.split(":", 1)[1].strip()
            skills.append((name, desc))
        except OSError:
            continue

    if not skills:
        return None

    lines = ["# Available Skills", ""]
    for name, desc in skills:
        if desc:
            lines.append(f"- **{name}**: {desc}")
        else:
            lines.append(f"- **{name}**")
    lines.append("")
    lines.append(
        f"Full skill files are at `{skills_dir}/`. "
        "Read a skill file when you need the detailed instructions."
    )
    return "\n".join(lines)
