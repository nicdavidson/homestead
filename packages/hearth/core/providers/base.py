"""
Hearth Core - Base Provider

Abstract interface for model providers (XAI, Anthropic, OpenAI, etc.)
Makes adding new models trivial.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    """Response from a model provider."""
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"
    metadata: Optional[Dict[str, Any]] = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class BaseProvider(ABC):
    """
    Base interface for all model providers.

    To add a new provider:
    1. Subclass BaseProvider
    2. Implement _call_api() and cost_per_token()
    3. Add to config.yaml
    4. Done!
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration.

        Args:
            config: Provider config from hearth.yaml, e.g.:
                {
                    "provider": "xai",
                    "model": "grok-3",
                    "api_key_env": "XAI_API_KEY",
                    "max_tokens": 2048,
                    "temperature": 0.7
                }
        """
        self.config = config
        self.model_name = config.get("model", "unknown")
        self.max_tokens = config.get("max_tokens", 2048)
        self.temperature = config.get("temperature", 0.7)

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name (xai, anthropic, openai, etc.)."""
        pass

    @abstractmethod
    def _call_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ProviderResponse:
        """
        Make the actual API call.

        Args:
            messages: Chat messages in OpenAI format
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            **kwargs: Provider-specific options

        Returns:
            ProviderResponse with content and token usage
        """
        pass

    @abstractmethod
    def cost_per_token(self) -> tuple[float, float]:
        """
        Return cost per token as (input_cost, output_cost) per million tokens.

        Examples:
            - Grok: (2.0, 10.0) = $2/M input, $10/M output
            - Sonnet: (3.0, 15.0) = $3/M input, $15/M output
            - Claude CLI: (0.0, 0.0) = free with Claude Pro
        """
        pass

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ProviderResponse:
        """
        Send chat messages and get a response.

        This is the main public interface. It wraps _call_api()
        with error handling and logging.

        Args:
            messages: Chat messages in OpenAI format:
                [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "..."}
                ]
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            **kwargs: Provider-specific options

        Returns:
            ProviderResponse with content and usage
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
            response = self._call_api(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return response
        except Exception as e:
            # Re-raise with provider context
            raise RuntimeError(f"{self.provider_name} API error: {e}") from e

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage."""
        input_cost_per_m, output_cost_per_m = self.cost_per_token()

        cost = (
            (input_tokens / 1_000_000 * input_cost_per_m) +
            (output_tokens / 1_000_000 * output_cost_per_m)
        )

        return cost

    def estimate_cost(self, messages: List[Dict[str, str]], estimated_output_tokens: int = 500) -> float:
        """
        Estimate cost for a request.

        Args:
            messages: The messages to send
            estimated_output_tokens: Estimated response length

        Returns:
            Estimated cost in dollars
        """
        # Rough token estimate: 1 token ≈ 4 characters
        input_chars = sum(len(m["content"]) for m in messages)
        input_tokens = input_chars // 4

        return self.calculate_cost(input_tokens, estimated_output_tokens)
