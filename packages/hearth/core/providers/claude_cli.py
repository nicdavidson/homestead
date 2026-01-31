"""
Hearth Core - Claude CLI Provider

Provider for Claude models via the Claude CLI.
Free with Claude Pro, no API key needed.
"""

import subprocess
import json
from typing import List, Dict, Any, Optional

from .base import BaseProvider, ProviderResponse


class ClaudeCLIProvider(BaseProvider):
    """
    Provider for Claude models via CLI.

    Uses the `claude` CLI command (https://github.com/anthropics/claude-code)
    which is free with Claude Pro subscription.

    Configuration example:
    ```yaml
    sonnet:
      provider: claude-cli
      model: claude-sonnet-4-5-20250929
      max_tokens: 4096
      temperature: 0.7
    ```

    Requirements:
    - Claude CLI installed: npm install -g @anthropic-ai/claude-code
    - Authenticated: claude auth
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Check if claude CLI is available
        try:
            result = subprocess.run(
                ['which', 'claude'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise FileNotFoundError(
                    "Claude CLI not found. Install: npm install -g @anthropic-ai/claude-code"
                )
        except Exception as e:
            raise RuntimeError(f"Failed to check Claude CLI: {e}")

    @property
    def provider_name(self) -> str:
        return "claude-cli"

    def _call_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ProviderResponse:
        """Make API call via Claude CLI."""
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        # Convert messages to prompt format
        # Claude CLI expects a single prompt, so we'll combine system + messages
        prompt_parts = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                prompt_parts.append(f"<system>\n{content}\n</system>\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")

        prompt = "\n".join(prompt_parts)

        # Build command
        # Note: Claude CLI doesn't support --max-tokens or --temperature flags
        # Those are controlled by API settings, not CLI flags
        cmd = [
            'claude',
            '-p', prompt,
            '--model', self.model_name,
            '--output-format', 'json'
        ]

        # Add any extra flags from kwargs
        if kwargs.get('no_history'):
            cmd.append('--no-history')

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"Claude CLI failed: {error_msg}")

            # Parse JSON response
            try:
                data = json.loads(result.stdout)
                # Claude CLI returns structured JSON with metadata
                # Extract the actual content
                if 'content' in data:
                    content = data['content']
                elif 'response' in data:
                    content = data['response']
                elif 'result' in data:
                    content = data['result']
                else:
                    # Fallback: use stdout as-is
                    content = result.stdout
            except json.JSONDecodeError:
                # Fallback: treat stdout as plain text
                content = result.stdout

            # Extract usage if available
            usage = data.get('usage', {}) if isinstance(data, dict) else {}
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)

            # Estimate if not available (rough approximation)
            if input_tokens == 0:
                input_tokens = len(prompt) // 4
            if output_tokens == 0:
                output_tokens = len(content) // 4

            return ProviderResponse(
                content=content,
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason="stop",
                metadata={
                    "cli_output": result.stdout,
                    "raw_data": data if isinstance(data, dict) else None
                }
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude CLI timed out after 2 minutes")

    def cost_per_token(self) -> tuple[float, float]:
        """
        Claude CLI is free with Claude Pro.

        If using API directly:
        - Sonnet: $3/M input, $15/M output
        - Opus: $15/M input, $75/M output

        We return (0.0, 0.0) for CLI since it's included with subscription.
        """
        return (0.0, 0.0)
