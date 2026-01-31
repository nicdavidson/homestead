"""
Hearth Agents - Base Agent Class
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Generator
from dataclasses import dataclass

from core import Config, get_config, CostTracker, Identity


@dataclass
class AgentResponse:
    """Response from an agent."""
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def usage_summary(self) -> str:
        return f"{self.input_tokens + self.output_tokens} tokens, ${self.cost:.4f}"


class BaseAgent(ABC):
    """
    Base class for all agents.
    Handles common functionality like context building and cost tracking.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.costs = CostTracker(config)
        self.identity = Identity(config)
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name/identifier."""
        pass
    
    @property
    @abstractmethod
    def model_tier(self) -> str:
        """Return the tier (grok, sonnet, opus)."""
        pass
    
    @abstractmethod
    def _call_api(
        self,
        messages: list,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AgentResponse:
        """Make the actual API call. Implemented by subclasses."""
        pass
    
    def chat(
        self,
        message: str,
        context: Optional[list] = None,
        include_identity: bool = True,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AgentResponse:
        """
        Send a message and get a response.
        
        Args:
            message: User message
            context: Optional conversation history
            include_identity: Whether to include soul.md etc in system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            AgentResponse with content and usage info
        """
        messages = []
        
        # Build system prompt
        if include_identity:
            system = self.identity.build_system_prompt()
        else:
            system = "You are a helpful assistant."
        
        messages.append({"role": "system", "content": system})
        
        # Add context/history
        if context:
            messages.extend(context)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call API
        response = self._call_api(messages, max_tokens, temperature)
        
        # Log costs
        self.costs.log_usage(
            model=self.model_tier,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            metadata={"message_preview": message[:100]}
        )
        
        return response
    
    def reflect(self) -> AgentResponse:
        """Trigger a self-reflection."""
        prompt = self.identity.build_reflection_prompt()
        return self.chat(prompt, include_identity=False, max_tokens=1500)
    
    def mock_response(self, message: str) -> AgentResponse:
        """Return a mock response for testing."""
        return AgentResponse(
            content=f"[MOCK {self.model_tier}] Received: {message[:50]}...",
            model=self.model_name,
            input_tokens=len(message) // 4,
            output_tokens=50,
            cost=0.0,
            metadata={"mock": True}
        )
