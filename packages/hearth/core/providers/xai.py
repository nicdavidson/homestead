"""
Hearth Core - XAI Provider

Provider for xAI models (Grok-3, etc.)
Cheap, fast, always-on workers.
"""

import os
from typing import List, Dict, Any, Optional
import httpx

from .base import BaseProvider, ProviderResponse


class XAIProvider(BaseProvider):
    """
    Provider for xAI's Grok models.

    Configuration example:
    ```yaml
    grok:
      provider: xai
      model: grok-3
      api_key_env: XAI_API_KEY
      max_tokens: 2048
      temperature: 0.7
    ```
    """

    API_BASE = "https://api.x.ai/v1"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Get API key from environment
        api_key_env = config.get("api_key_env", "XAI_API_KEY")
        self.api_key = os.getenv(api_key_env)

        if not self.api_key:
            raise ValueError(f"{api_key_env} environment variable not set")

    @property
    def provider_name(self) -> str:
        return "xai"

    def _call_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ProviderResponse:
        """Make API call to xAI."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
        }

        # Add any extra kwargs
        payload.update(kwargs)

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.API_BASE}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        # Extract response
        content = data["choices"][0]["message"]["content"]
        finish_reason = data["choices"][0].get("finish_reason", "stop")
        usage = data.get("usage", {})

        return ProviderResponse(
            content=content,
            model=data.get("model", self.model_name),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=finish_reason,
            metadata={"raw_response": data}
        )

    def cost_per_token(self) -> tuple[float, float]:
        """
        Grok-3 pricing (as of Jan 2026):
        - Input: $2 per million tokens
        - Output: $10 per million tokens
        """
        return (2.0, 10.0)
