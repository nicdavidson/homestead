from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class AgentIdentity:
    """Who is sending a message — used for multi-agent TG visibility."""

    name: str
    display_name: str
    emoji: str
    model_tier: str  # "grok", "sonnet", "opus", "claude-cli"


@dataclass
class LogEntry:
    timestamp: float
    level: str
    source: str
    message: str
    data: dict | None = None
    session_id: str | None = None
    chat_id: int | None = None
    id: int | None = None


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

AGENTS: dict[str, AgentIdentity] = {
    "herald": AgentIdentity("herald", "Herald", "\U0001f4ef", "claude-cli"),
    "nightshift": AgentIdentity("nightshift", "Nightshift", "\U0001f319", "sonnet"),
    "researcher": AgentIdentity("researcher", "Research", "\U0001f50d", "grok"),
    "steward": AgentIdentity("steward", "Steward", "\U0001f4cb", "sonnet"),
    "hearth": AgentIdentity("hearth", "Hearth", "\U0001f3e0", "sonnet"),
}


def format_agent_message(agent_name: str, text: str) -> str:
    """Format a message with agent identity prefix.

    Default herald messages have no prefix. Other agents get emoji + bold name.
    """
    if agent_name == "herald":
        return text
    agent = AGENTS.get(agent_name)
    if agent is None:
        return f"<b>[{agent_name}]</b>\n\n{text}"
    return f"{agent.emoji} <b>{agent.display_name}</b>\n\n{text}"
