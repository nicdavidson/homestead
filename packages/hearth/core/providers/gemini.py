"""
Hearth Core - Google Gemini Provider

Provider for Google Gemini models (Gemini Pro, Ultra, Flash)
"""

import os
from typing import List, Dict, Any, Optional
import httpx

from .base import BaseProvider, ProviderResponse


class GeminiProvider(BaseProvider):
    """
    Provider for Google Gemini models.

    Configuration example:
    ```yaml
    gemini-pro:
      provider: gemini
      model: gemini-pro
      api_key_env: GOOGLE_API_KEY
      max_tokens: 2048
      temperature: 0.7
    ```

    Supported models:
    - gemini-pro (latest)
    - gemini-1.5-pro
    - gemini-1.5-flash
    - gemini-ultra (when available)
    """

    API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Get API key from environment
        api_key_env = config.get("api_key_env", "GOOGLE_API_KEY")
        self.api_key = os.getenv(api_key_env)

        if not self.api_key:
            raise ValueError(f"{api_key_env} environment variable not set")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _convert_messages_to_gemini_format(
        self, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Convert OpenAI-style messages to Gemini format.

        Gemini expects:
        {
            "contents": [
                {
                    "role": "user",  # or "model"
                    "parts": [{"text": "content"}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": "system prompt"}]
            }
        }
        """
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                # Gemini handles system messages separately
                system_instruction = {
                    "parts": [{"text": content}]
                }
            elif role == "assistant":
                # Gemini uses "model" instead of "assistant"
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
            else:
                # "user" role
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })

        result = {"contents": contents}
        if system_instruction:
            result["systemInstruction"] = system_instruction

        return result

    def _call_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ProviderResponse:
        """Make API call to Google Gemini."""
        # Convert messages to Gemini format
        gemini_payload = self._convert_messages_to_gemini_format(messages)

        # Add generation config
        gemini_payload["generationConfig"] = {
            "maxOutputTokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
        }

        # Build URL with API key
        url = f"{self.API_BASE}/models/{self.model_name}:generateContent"
        params = {"key": self.api_key}

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                json=gemini_payload,
                params=params
            )
            response.raise_for_status()
            data = response.json()

        # Extract response
        # Gemini response format:
        # {
        #   "candidates": [
        #     {
        #       "content": {
        #         "parts": [{"text": "response"}],
        #         "role": "model"
        #       },
        #       "finishReason": "STOP"
        #     }
        #   ],
        #   "usageMetadata": {
        #     "promptTokenCount": 10,
        #     "candidatesTokenCount": 20,
        #     "totalTokenCount": 30
        #   }
        # }

        candidate = data["candidates"][0]
        content = candidate["content"]["parts"][0]["text"]
        finish_reason = candidate.get("finishReason", "STOP")

        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)

        # Map Gemini finish reasons to standard ones
        finish_reason_map = {
            "STOP": "stop",
            "MAX_TOKENS": "length",
            "SAFETY": "content_filter",
            "RECITATION": "content_filter",
            "OTHER": "stop"
        }
        mapped_reason = finish_reason_map.get(finish_reason, "stop")

        return ProviderResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=mapped_reason,
            metadata={"raw_response": data}
        )

    def cost_per_token(self) -> tuple[float, float]:
        """
        Google Gemini pricing (as of Jan 2026, approximate):

        Gemini 1.5 Pro:
        - Input: $3.50 per million tokens (up to 128k)
        - Output: $10.50 per million tokens

        Gemini 1.5 Flash:
        - Input: $0.35 per million tokens (up to 128k)
        - Output: $1.05 per million tokens

        Gemini Pro (legacy):
        - Input: $0.50 per million tokens
        - Output: $1.50 per million tokens

        Gemini Ultra (when available):
        - Estimated higher than Pro
        """
        model = self.model_name.lower()

        if "1.5-flash" in model or "flash" in model:
            return (0.35, 1.05)
        elif "1.5-pro" in model:
            return (3.5, 10.5)
        elif "ultra" in model:
            # Estimate higher than Pro
            return (10.0, 30.0)
        elif "pro" in model:
            # Legacy gemini-pro
            return (0.5, 1.5)
        else:
            # Default to 1.5 Pro pricing
            return (3.5, 10.5)
