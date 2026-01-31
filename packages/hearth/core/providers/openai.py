"""
Hearth Core - OpenAI Provider

Provider for OpenAI models (GPT-4, GPT-3.5, etc.)
"""

import os
from typing import List, Dict, Any, Optional
import httpx

from .base import BaseProvider, ProviderResponse


class OpenAIProvider(BaseProvider):
    """
    Provider for OpenAI models.

    Configuration example:
    ```yaml
    gpt4:
      provider: openai
      model: gpt-4-turbo-preview
      api_key_env: OPENAI_API_KEY
      max_tokens: 4096
      temperature: 0.7
    ```

    Supported models:
    - gpt-4-turbo-preview
    - gpt-4
    - gpt-3.5-turbo
    - gpt-3.5-turbo-16k
    """

    API_BASE = "https://api.openai.com/v1"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Get API key from environment
        api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
        self.api_key = os.getenv(api_key_env)

        if not self.api_key:
            raise ValueError(f"{api_key_env} environment variable not set")

    @property
    def provider_name(self) -> str:
        return "openai"

    def _call_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ProviderResponse:
        """Make API call to OpenAI."""
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
        OpenAI pricing (as of Jan 2026, approximate):

        GPT-4 Turbo:
        - Input: $10 per million tokens
        - Output: $30 per million tokens

        GPT-4:
        - Input: $30 per million tokens
        - Output: $60 per million tokens

        GPT-3.5 Turbo:
        - Input: $0.50 per million tokens
        - Output: $1.50 per million tokens

        Default to GPT-4 Turbo pricing.
        """
        model = self.model_name.lower()

        if "gpt-4-turbo" in model or "gpt-4-1106" in model:
            return (10.0, 30.0)
        elif "gpt-4" in model:
            return (30.0, 60.0)
        elif "gpt-3.5" in model:
            return (0.5, 1.5)
        else:
            # Default to GPT-4 pricing for safety
            return (30.0, 60.0)
