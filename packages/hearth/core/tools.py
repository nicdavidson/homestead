"""
Hearth Core - Tools for Agent Spawning

Tools that agents can use to spawn and manage subagents.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    """Definition of a tool that agents can call."""
    name: str
    description: str
    input_schema: dict


# Tool definitions following Claude API tool format
SPAWN_AGENT_TOOL = ToolDefinition(
    name="spawn_agent",
    description="""Spawn a subagent to handle a specific task asynchronously.

Use this when you need to:
- Delegate work to a cheaper/specialized agent (e.g., Grok for simple tasks)
- Run multiple tasks in parallel
- Offload time-consuming research or analysis

The subagent will run independently and announce results when complete.
You'll receive the run_id immediately - the subagent executes in the background.

Guidelines:
- Use Grok for: simple tasks, research, data gathering, HA commands (~$0.01/task)
- Use Sonnet for: complex reasoning, creative work, synthesis (~$0 via CLI)
- Use Opus for: deep thinking, philosophical questions, major decisions (~$0 via CLI)

Returns immediately with run_id and session_key. Results announced later.""",
    input_schema={
        "type": "object",
        "properties": {
            "agent_type": {
                "type": "string",
                "enum": ["grok", "sonnet", "opus"],
                "description": "Type of agent to spawn (grok=cheap worker, sonnet=mid-tier, opus=deep thinking)"
            },
            "task": {
                "type": "string",
                "description": "Clear description of what the subagent should do"
            },
            "label": {
                "type": "string",
                "description": "Optional human-readable label for tracking (e.g., 'research-api-docs')"
            }
        },
        "required": ["agent_type", "task"]
    }
)

LIST_SUBAGENTS_TOOL = ToolDefinition(
    name="list_subagents",
    description="""List all active subagent sessions spawned by you.

Shows:
- run_id: Unique identifier
- agent_type: grok/sonnet/opus
- status: running/completed/failed
- task: What the subagent is working on
- spawned_at: When it was created
- results: Available when status=completed

Use this to check on progress of spawned agents.""",
    input_schema={
        "type": "object",
        "properties": {
            "status_filter": {
                "type": "string",
                "enum": ["all", "running", "completed", "failed"],
                "description": "Filter by status (default: all)"
            }
        }
    }
)


def get_available_tools(session_id: str) -> List[ToolDefinition]:
    """
    Get tools available based on session role (not agent type).

    The distinction is ROLE-based:
    - Main conversation agents (talking to user) → Can spawn subagents
    - Subagents (spawned workers) → Cannot spawn (prevents nesting)

    This means:
    - Grok as main agent → Gets spawn tools
    - Opus as subagent → No spawn tools

    Args:
        session_id: Session identifier
            - "main", "cli-*", "web-*", "telegram-*" → Main conversation
            - "subagent:*" → Spawned worker (no tools)

    Returns:
        List of tool definitions
    """
    # Subagents cannot spawn subagents (no nesting)
    if session_id.startswith("subagent:"):
        return []

    # Main conversation agents can spawn, regardless of model type
    return [SPAWN_AGENT_TOOL, LIST_SUBAGENTS_TOOL]


def format_tools_for_cli(tools: List[ToolDefinition]) -> List[Dict]:
    """
    Format tool definitions for Claude CLI.

    Returns list of dicts in Claude API tool format:
    {
        "name": "tool_name",
        "description": "what it does",
        "input_schema": {...}
    }
    """
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema
        }
        for tool in tools
    ]
