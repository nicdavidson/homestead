"""
Hearth Core - Session Management
Manages subagent sessions (clawd-style spawning pattern).
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from .state import StateDB, get_state
from .config import Config, get_config

logger = logging.getLogger("hearth.sessions")


@dataclass
class SubagentSession:
    """Represents a spawned subagent session."""
    run_id: str
    session_key: str
    agent_type: str  # grok, sonnet, opus
    task: str
    label: Optional[str]
    spawned_by: str  # session_id of parent
    spawned_at: datetime
    status: str = "running"  # running, completed, error, timeout
    result: Optional[str] = None
    completed_at: Optional[datetime] = None
    tokens_used: Dict[str, int] = field(default_factory=dict)
    cost: float = 0.0


class SessionManager:
    """
    Manages subagent sessions.

    Clawd-style pattern:
    - spawn_agent() returns immediately with run_id
    - Subagent runs in background
    - Results announced back to parent session
    """

    def __init__(self, config: Optional[Config] = None, state: Optional[StateDB] = None):
        self.config = config or get_config()
        self.state = state or get_state(str(self.config.data_dir / "hearth.db"))
        self._active_sessions: Dict[str, SubagentSession] = {}
        self._announce_callbacks: Dict[str, Callable] = {}
        # ThreadPoolExecutor for background subagent execution (max 3 concurrent)
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="subagent")

    def spawn_agent(
        self,
        agent_type: str,
        task: str,
        spawned_by: str,
        label: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Spawn a subagent (non-blocking).

        Returns immediately with:
        {
            "status": "accepted",
            "run_id": "uuid",
            "session_key": "agent:sonnet:subagent:uuid"
        }
        """
        # Validate agent type
        spawnable = self.config.get('agents.spawnable', ['grok', 'sonnet'])
        if agent_type not in spawnable:
            raise ValueError(f"Agent type '{agent_type}' not in spawnable list: {spawnable}")

        # Generate IDs
        run_id = str(uuid.uuid4())
        session_key = f"subagent:{agent_type}:{run_id}"

        # Create session
        session = SubagentSession(
            run_id=run_id,
            session_key=session_key,
            agent_type=agent_type,
            task=task,
            label=label,
            spawned_by=spawned_by,
            spawned_at=datetime.now()
        )

        self._active_sessions[run_id] = session

        # Log to state DB
        self.state.set(f"subagent:{run_id}:task", task)
        self.state.set(f"subagent:{run_id}:agent_type", agent_type)
        self.state.set(f"subagent:{run_id}:status", "running")

        # Submit to executor for background execution
        self._executor.submit(self._execute_subagent, session)
        logger.info(f"Spawned {agent_type} subagent: {run_id} (label: {label})")

        return {
            "status": "accepted",
            "run_id": run_id,
            "session_key": session_key
        }

    def list_subagents(self, spawned_by: Optional[str] = None) -> List[Dict]:
        """List active subagent sessions."""
        sessions = []

        for session in self._active_sessions.values():
            if spawned_by and session.spawned_by != spawned_by:
                continue

            sessions.append({
                "run_id": session.run_id,
                "agent_type": session.agent_type,
                "task": session.task[:100],  # Truncate long tasks
                "label": session.label,
                "status": session.status,
                "spawned_at": session.spawned_at.isoformat(),
                "runtime_seconds": (datetime.now() - session.spawned_at).total_seconds()
                    if session.status == "running" else None
            })

        return sessions

    def complete_subagent(
        self,
        run_id: str,
        result: str,
        status: str = "completed",
        tokens_used: Optional[Dict[str, int]] = None,
        cost: float = 0.0
    ):
        """Mark a subagent session as complete and announce results."""
        if run_id not in self._active_sessions:
            return

        session = self._active_sessions[run_id]
        session.status = status
        session.result = result
        session.completed_at = datetime.now()
        session.tokens_used = tokens_used or {}
        session.cost = cost

        # Update state DB
        self.state.set(f"subagent:{run_id}:status", status)
        self.state.set(f"subagent:{run_id}:result", result)

        # Announce back to parent session
        if session.spawned_by in self._announce_callbacks:
            callback = self._announce_callbacks[session.spawned_by]
            callback(session)

        # Archive after completion
        # TODO: Implement archival after timeout (clawd uses 60 min)

    def register_announce_callback(self, session_id: str, callback: Callable):
        """Register a callback for when subagents announce completion."""
        self._announce_callbacks[session_id] = callback

    def get_session(self, run_id: str) -> Optional[SubagentSession]:
        """Get a subagent session by run_id."""
        return self._active_sessions.get(run_id)

    def _execute_subagent(self, session: SubagentSession):
        """
        Execute subagent task (runs in background thread).

        This method:
        1. Gets the agent instance
        2. Sends the task
        3. Waits for response
        4. Completes or fails the session
        """
        try:
            logger.info(f"Executing subagent {session.run_id}: {session.task[:100]}...")

            # Get agent instance
            agent = self._get_agent_instance(session.agent_type)

            # Execute task
            response = agent.chat(
                message=session.task,
                include_identity=False,  # Subagents don't need full identity
                max_tokens=1024,  # Keep subagent responses reasonable
                temperature=0.7
            )

            # Complete session with results
            self.complete_subagent(
                run_id=session.run_id,
                result=response.content,
                status="completed",
                tokens_used={
                    "input": response.input_tokens,
                    "output": response.output_tokens
                },
                cost=response.cost
            )

            logger.info(f"Subagent {session.run_id} completed successfully")

        except Exception as e:
            logger.error(f"Subagent {session.run_id} failed: {e}")
            self.complete_subagent(
                run_id=session.run_id,
                result=f"Error: {str(e)}",
                status="error",
                cost=0.0
            )

    def _get_agent_instance(self, agent_type: str):
        """Get agent instance by type."""
        # Lazy import to avoid circular dependencies
        from agents import GrokAgent, SonnetAgent, OpusAgent

        if agent_type == "grok":
            return GrokAgent(self.config)
        elif agent_type == "sonnet":
            return SonnetAgent(self.config)
        elif agent_type == "opus":
            return OpusAgent(self.config)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    def shutdown(self):
        """Shutdown the executor (waits for running tasks to complete)."""
        logger.info("Shutting down session manager...")
        self._executor.shutdown(wait=True)
        logger.info("Session manager shutdown complete")


# Global instance
_session_manager: Optional[SessionManager] = None

def get_session_manager(config: Optional[Config] = None) -> SessionManager:
    """Get or create the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(config)
    return _session_manager
