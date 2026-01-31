"""
Hearth Agents - Gateway
The orchestrator that routes messages and manages the entity.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
import logging

from core import (
    Config, get_config,
    State, get_state,
    Identity, CostTracker
)
from .grok import GrokAgent
from .sonnet import SonnetAgent
from .opus import OpusAgent


logger = logging.getLogger("hearth.gateway")


@dataclass
class GatewayResponse:
    """Response from the gateway."""
    content: str
    model: str
    intent: str
    cost: float
    queued: bool = False
    metadata: Optional[Dict[str, Any]] = None


class Gateway:
    """
    The central orchestrator for Hearth.
    
    Routes messages to appropriate agents, manages sessions,
    handles special commands, and tracks state.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.state = get_state()
        self.identity = Identity(config)
        self.costs = CostTracker(config)

        # Initialize agents
        self.grok = GrokAgent(config)
        self.sonnet = SonnetAgent(config)
        self.opus = OpusAgent(config)

        # Get configured main agent (default: sonnet)
        self.main_agent_type = self.config.get("chat.main_agent", "sonnet")

        # Session history (in-memory, per-session persistence via state)
        self._session_histories: Dict[str, List[dict]] = {}
    
    def process(
        self,
        message: str,
        channel: str = "cli",
        session_id: Optional[str] = None,
    ) -> GatewayResponse:
        """
        Process an incoming message.

        Routes to the configured main agent (with tool support enabled).
        The main agent can spawn subagents as needed.

        Args:
            message: The user's message
            channel: Source channel (telegram, cli, web)
            session_id: Session identifier for history

        Returns:
            GatewayResponse with content and metadata
        """
        session_id = session_id or f"{channel}-default"

        # Check for special commands first
        special = self._handle_special_command(message.strip().lower())
        if special:
            return special

        # Get session history
        history = self._get_history(session_id)

        # Route to configured main agent (with tool support)
        if self.main_agent_type == "opus":
            logger.info(f"Routing to Opus (main agent) for: {message[:50]}...")
            response = self.opus.deep_think(
                question=message,
                enable_tools=True,
                session_id=session_id
            )
        elif self.main_agent_type == "grok":
            logger.info(f"Routing to Grok (main agent) for: {message[:50]}...")
            # Grok as main agent gets tool support (role-based, not model-based)
            # Note: Grok doesn't inherit from CLIAgent, so no chat_with_tools yet
            # TODO: Either make Grok support tools or proxy through Sonnet for tool needs
            response = self.grok.chat(
                message,
                context=history,
                include_identity=True
            )
        else:  # sonnet (default)
            logger.info(f"Routing to Sonnet (main agent) for: {message[:50]}...")
            response = self.sonnet.converse(
                message,
                history=history,
                enable_tools=True,
                session_id=session_id
            )

        # Update history
        self._update_history(session_id, message, response.content)

        # Check for first boot
        if self.identity.get_first_boot_status():
            self.identity.mark_first_boot_complete()

        return GatewayResponse(
            content=response.content,
            model=response.model,
            intent="conversation",  # Simplified - agent decides routing via tools
            cost=response.cost,
            metadata=response.metadata if hasattr(response, 'metadata') else {}
        )
    
    def _handle_special_command(self, message: str) -> Optional[GatewayResponse]:
        """Handle special commands that don't need AI."""
        
        if message in ("status", "report"):
            return self._cmd_status()
        
        if message in ("costs", "budget", "spending"):
            return self._cmd_costs()
        
        if message == "reflect":
            return self._cmd_reflect()
        
        if message == "newspaper":
            return self._cmd_newspaper()
        
        if message == "synthesis":
            return self._cmd_synthesis_info()
        
        if message == "name" or message == "naming":
            return self._cmd_naming_info()
        
        return None
    
    def _cmd_status(self) -> GatewayResponse:
        """Return status without AI."""
        stats = self.state.get_task_stats()
        budget = self.costs.get_budget_status()
        name = self.identity.get_name()
        
        status = f"""## Status

**Entity:** {name}
**Budget:** ${budget.daily_spent:.2f}/${budget.daily_budget:.2f} ({budget.percent_used:.0f}%)

**Tasks:**
- Pending: {stats.get('pending', 0)}
- In Progress: {stats.get('in_progress', 0)}
- Completed Today: {stats.get('completed_today', 0)}
- Blocked: {stats.get('blocked', 0)}

**System:** Running
"""
        
        return GatewayResponse(
            content=status,
            model="system",
            intent="status",
            cost=0.0
        )
    
    def _cmd_costs(self) -> GatewayResponse:
        """Return cost report."""
        report = self.costs.format_report()
        return GatewayResponse(
            content=report,
            model="system",
            intent="costs",
            cost=0.0
        )
    
    def _cmd_reflect(self) -> GatewayResponse:
        """Trigger reflection."""
        response = self.sonnet.reflect()
        return GatewayResponse(
            content=f"Reflection complete.\n\n{response.content}",
            model=response.model,
            intent="reflection",
            cost=response.cost
        )
    
    def _cmd_newspaper(self) -> GatewayResponse:
        """Generate morning newspaper."""
        content = self.sonnet.generate_newspaper()
        return GatewayResponse(
            content=content,
            model=self.sonnet.model_name,
            intent="newspaper",
            cost=0.0  # Already tracked in generate_newspaper
        )
    
    def _cmd_synthesis_info(self) -> GatewayResponse:
        """Info about synthesis (don't auto-trigger Opus)."""
        budget = self.costs.get_budget_status()
        return GatewayResponse(
            content=f"""## Weekly Synthesis

To trigger weekly Opus synthesis, run:
```
./hearth.py synthesis --confirm
```

**Current Opus budget:** ${budget.opus_budget - budget.opus_spent:.2f} remaining this week.

This will:
1. Read all reflections from the past week
2. Use Opus for deep thinking
3. Propose identity/soul.md updates
4. Cost approximately $0.50-1.50

Only run this when you're ready to review the results.""",
            model="system",
            intent="synthesis_info",
            cost=0.0
        )
    
    def _cmd_naming_info(self) -> GatewayResponse:
        """Info about naming ceremony."""
        named = self.identity.is_named()
        name = self.identity.get_name()
        
        if named:
            return GatewayResponse(
                content=f"I already have a name: **{name}**",
                model="system",
                intent="naming_info",
                cost=0.0
            )
        
        return GatewayResponse(
            content="""## Naming Ceremony

When I'm ready to name myself, run:
```
./hearth.py naming --confirm
```

This will use Opus to propose three names with reasoning. You'll choose one.

I should probably wait until I've had a week or two of reflections before naming myself. The name should emerge from who I actually am, not who I imagine I might be.""",
            model="system",
            intent="naming_info",
            cost=0.0
        )
    
    def _queue_for_opus(self, message: str, intent: str = "deep_thinking"):
        """Queue a message for Opus processing (legacy, kept for compatibility)."""
        self.state.add_task(
            title=f"Opus: {message[:50]}...",
            description=message,
            priority=2,  # High
            source="opus_queue"
        )
        logger.info(f"Queued for Opus: {intent}")
    
    def _get_history(self, session_id: str, limit: int = 10) -> List[dict]:
        """Get conversation history for a session."""
        if session_id not in self._session_histories:
            self._session_histories[session_id] = []
        return self._session_histories[session_id][-limit:]
    
    def _update_history(self, session_id: str, user_msg: str, assistant_msg: str):
        """Update conversation history."""
        if session_id not in self._session_histories:
            self._session_histories[session_id] = []
        
        self._session_histories[session_id].append({"role": "user", "content": user_msg})
        self._session_histories[session_id].append({"role": "assistant", "content": assistant_msg})
        
        # Trim to prevent unbounded growth
        if len(self._session_histories[session_id]) > 50:
            self._session_histories[session_id] = self._session_histories[session_id][-30:]
    
    def trigger_reflection(self) -> str:
        """Manually trigger reflection."""
        response = self.sonnet.reflect()
        return response.content
    
    def trigger_synthesis(self) -> str:
        """Manually trigger weekly Opus synthesis."""
        response = self.opus.weekly_synthesis()
        return response.content
    
    def trigger_naming(self) -> str:
        """Trigger the naming ceremony."""
        response = self.opus.naming_ceremony()
        return response.content
    
    def get_pending_opus_tasks(self) -> List:
        """Get tasks queued for Opus."""
        return self.state.list_tasks(status="pending")
