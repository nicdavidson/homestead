"""
Hearth Core - Message Router
Routes messages to the appropriate model based on intent and context.
"""

import re
from enum import Enum
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

from .config import Config, get_config
from .costs import CostTracker


class ModelTier(str, Enum):
    GROK = "grok"
    SONNET = "sonnet"
    OPUS = "opus"


class Intent(str, Enum):
    # Simple (Grok)
    STATUS = "status"
    COSTS = "costs"
    HA_COMMAND = "ha_command"
    SIMPLE_TASK = "simple_task"
    QUICK_LOOKUP = "quick_lookup"
    
    # Medium (Sonnet)
    CONVERSATION = "conversation"
    REFLECTION = "reflection"
    SYNTHESIS = "synthesis"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    
    # Complex (Opus queue)
    IDENTITY = "identity"
    STRATEGIC = "strategic"
    DEEP_THINK = "deep_think"
    
    # Meta
    UNKNOWN = "unknown"


@dataclass
class RoutingDecision:
    model: ModelTier
    intent: Intent
    reason: str
    should_queue: bool = False
    needs_context: bool = True


# Intent patterns
INTENT_PATTERNS = {
    # Status commands
    Intent.STATUS: [
        r"^status$", r"^how are you", r"^what.*doing", r"^report$",
    ],
    Intent.COSTS: [
        r"^costs?$", r"^budget$", r"^spending$", r"^how much",
    ],
    
    # HA commands
    Intent.HA_COMMAND: [
        r"turn (on|off)", r"lights?", r"temperature", r"thermostat",
        r"goodnight", r"good morning", r"movie mode", r"away mode",
    ],
    
    # Reflection
    Intent.REFLECTION: [
        r"^reflect$", r"reflection", r"how do you feel", r"what.*learned",
    ],
    
    # Identity/deep
    Intent.IDENTITY: [
        r"who are you", r"what.*your name", r"name yourself",
        r"soul", r"identity", r"what do you want",
    ],
    Intent.STRATEGIC: [
        r"strategy", r"architecture", r"rethink", r"redesign",
        r"what should (we|i|you)", r"plan for",
    ],
    Intent.DEEP_THINK: [
        r"think deeply", r"analyze.*thoroughly", r"synthesis",
        r"weekly review", r"opus",
    ],
    
    # Creative
    Intent.CREATIVE: [
        r"write", r"draft", r"compose", r"blog", r"article", r"story",
    ],
    
    # Simple tasks
    Intent.SIMPLE_TASK: [
        r"remind", r"todo", r"add task", r"check", r"look up",
    ],
}


class Router:
    """
    Routes messages to appropriate models.
    Grok handles simple stuff. Sonnet thinks. Opus is reserved.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.costs = CostTracker(config)
    
    def classify_intent(self, message: str) -> Intent:
        """Classify message intent based on patterns."""
        message_lower = message.lower().strip()
        
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        # Default heuristics
        if len(message) < 20:
            return Intent.SIMPLE_TASK
        elif "?" in message:
            return Intent.CONVERSATION
        else:
            return Intent.UNKNOWN
    
    def route(self, message: str, context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        Determine routing for a message.
        
        Returns routing decision with model, intent, and reasoning.
        """
        intent = self.classify_intent(message)
        context = context or {}
        
        # Map intents to models
        if intent in (Intent.STATUS, Intent.COSTS, Intent.HA_COMMAND, 
                      Intent.SIMPLE_TASK, Intent.QUICK_LOOKUP):
            model = ModelTier.GROK
            reason = "Simple command or task"
            needs_context = intent not in (Intent.STATUS, Intent.COSTS)
        
        elif intent in (Intent.CONVERSATION, Intent.REFLECTION, 
                        Intent.SYNTHESIS, Intent.CREATIVE, Intent.ANALYSIS):
            model = ModelTier.SONNET
            reason = "Requires thinking or personality"
            needs_context = True
        
        elif intent in (Intent.IDENTITY, Intent.STRATEGIC, Intent.DEEP_THINK):
            model = ModelTier.OPUS
            reason = "Deep thinking required - queued for manual trigger"
            needs_context = True
            return RoutingDecision(
                model=model,
                intent=intent,
                reason=reason,
                should_queue=True,  # Don't auto-trigger Opus
                needs_context=needs_context
            )
        
        else:
            # Default to Sonnet for unknown
            model = ModelTier.SONNET
            reason = "General conversation"
            needs_context = True
        
        # Check budget
        can_use, budget_reason = self.costs.can_use_model(model.value)
        
        if not can_use:
            # Fall back to cheaper model
            if model == ModelTier.SONNET:
                model = ModelTier.GROK
                reason = f"Budget constraint: {budget_reason}. Using Grok instead."
            elif model == ModelTier.OPUS:
                return RoutingDecision(
                    model=model,
                    intent=intent,
                    reason=f"Queued. {budget_reason}",
                    should_queue=True,
                    needs_context=needs_context
                )
        
        return RoutingDecision(
            model=model,
            intent=intent,
            reason=reason,
            should_queue=False,
            needs_context=needs_context
        )
    
    def should_escalate(self, grok_response: str, original_message: str) -> bool:
        """
        Determine if Grok's response indicates we should escalate to Sonnet.
        """
        escalation_signals = [
            "i'm not sure",
            "this is complex",
            "you should ask",
            "i can't",
            "beyond my",
            "need more context",
            "escalate",
        ]
        
        response_lower = grok_response.lower()
        for signal in escalation_signals:
            if signal in response_lower:
                return True
        
        # If response is very short for a complex question
        if len(original_message) > 100 and len(grok_response) < 50:
            return True
        
        return False
    
    def format_routing_info(self, decision: RoutingDecision) -> str:
        """Format routing decision for logging/display."""
        status = "🚀 Queued" if decision.should_queue else "→"
        return f"[{decision.intent.value}] {status} {decision.model.value}: {decision.reason}"
