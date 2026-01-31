"""
Hearth Agents - Tool Executor

Handles tool execution for agent spawning and management.
"""

import json
import logging
from typing import Dict, Any, Optional

from core import SessionManager, get_session_manager, Config

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes tools called by agents.

    Handles:
    - spawn_agent: Create new subagent sessions
    - list_subagents: Show active subagent sessions
    """

    def __init__(self, config: Config, session_manager: Optional[SessionManager] = None):
        self.config = config
        self.session_manager = session_manager or get_session_manager(config)

    def execute(self, tool_name: str, tool_input: Dict[str, Any], spawned_by: str) -> Dict[str, Any]:
        """
        Execute a tool and return results.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool input parameters
            spawned_by: Session ID of the agent calling the tool

        Returns:
            Tool execution result dict
        """
        if tool_name == "spawn_agent":
            return self._spawn_agent(tool_input, spawned_by)
        elif tool_name == "list_subagents":
            return self._list_subagents(tool_input, spawned_by)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _spawn_agent(self, tool_input: Dict[str, Any], spawned_by: str) -> Dict[str, Any]:
        """
        Execute spawn_agent tool.

        Args:
            tool_input: {
                "agent_type": "grok"|"sonnet"|"opus",
                "task": "description of task",
                "label": "optional label"
            }
            spawned_by: Session ID of spawning agent

        Returns:
            {
                "status": "accepted",
                "run_id": "uuid",
                "session_key": "subagent:type:uuid",
                "message": "human-readable confirmation"
            }
        """
        try:
            agent_type = tool_input.get("agent_type")
            task = tool_input.get("task")
            label = tool_input.get("label")

            # Validate agent type is spawnable
            spawnable = self.config.get("agents.spawnable", ["grok", "sonnet"])
            if agent_type not in spawnable:
                return {
                    "error": f"Agent type '{agent_type}' not in spawnable list: {spawnable}"
                }

            # Prevent nesting - subagents cannot spawn subagents
            if spawned_by.startswith("subagent:"):
                return {
                    "error": "Subagents cannot spawn subagents (no nesting allowed)"
                }

            # Spawn the agent
            result = self.session_manager.spawn_agent(
                agent_type=agent_type,
                task=task,
                spawned_by=spawned_by,
                label=label
            )

            # Add human-readable message
            result["message"] = (
                f"✓ Spawned {agent_type} agent (run_id: {result['run_id'][:8]}...). "
                f"Task: {task[:60]}{'...' if len(task) > 60 else ''}"
            )

            logger.info(f"Spawned {agent_type} subagent {result['run_id'][:8]} for {spawned_by}")

            return result

        except Exception as e:
            logger.error(f"spawn_agent failed: {e}")
            return {"error": str(e)}

    def _list_subagents(self, tool_input: Dict[str, Any], spawned_by: str) -> Dict[str, Any]:
        """
        Execute list_subagents tool.

        Args:
            tool_input: {
                "status_filter": "all"|"running"|"completed"|"failed"
            }
            spawned_by: Session ID of requesting agent

        Returns:
            {
                "subagents": [
                    {
                        "run_id": "uuid",
                        "agent_type": "grok",
                        "status": "running",
                        "task": "description",
                        "spawned_at": "ISO timestamp",
                        "label": "optional",
                        "results": {...} if completed
                    },
                    ...
                ],
                "count": 3
            }
        """
        try:
            status_filter = tool_input.get("status_filter", "all")

            # Get sessions spawned by this agent
            sessions = self.session_manager.list_subagents(
                spawned_by=spawned_by,
                status_filter=status_filter
            )

            # Format for readability
            formatted_sessions = []
            for session in sessions:
                formatted = {
                    "run_id": session.run_id,
                    "agent_type": session.agent_type,
                    "status": session.status,
                    "task": session.task,
                    "spawned_at": session.spawned_at.isoformat(),
                }

                if session.label:
                    formatted["label"] = session.label

                if session.status == "completed" and session.results:
                    formatted["results"] = session.results

                formatted_sessions.append(formatted)

            return {
                "subagents": formatted_sessions,
                "count": len(formatted_sessions)
            }

        except Exception as e:
            logger.error(f"list_subagents failed: {e}")
            return {"error": str(e)}
