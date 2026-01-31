"""
Hearth Agents - CLI-Based Agent Class

Uses Claude CLI subprocess calls instead of direct API calls.
Supports Claude Pro/Max subscriptions (no per-token costs).
"""

import json
import logging
import re
import subprocess
from abc import abstractmethod
from typing import Optional, List, Dict, Any

from .base import BaseAgent, AgentResponse

logger = logging.getLogger(__name__)


class CLIAgent(BaseAgent):
    """
    Base class for agents using Claude CLI subprocess calls.

    Executes `claude -p --output-format json --model <model>` to leverage
    Claude Pro/Max subscription without per-token costs.
    """

    def __init__(self, config: Optional['Config'] = None):
        super().__init__(config)
        self._verify_cli_available()

    @property
    @abstractmethod
    def cli_model_name(self) -> str:
        """Return the CLI model identifier (e.g., claude-sonnet-4-5-20250929)."""
        pass

    @property
    @abstractmethod
    def cli_timeout(self) -> int:
        """Return timeout in seconds for CLI calls."""
        pass

    def _verify_cli_available(self):
        """Verify Claude CLI is installed and accessible."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "Claude CLI found but returned error. "
                    "Run 'claude --version' to diagnose."
                )
            logger.debug(f"Claude CLI available: {result.stdout.strip()}")
        except FileNotFoundError:
            raise RuntimeError(
                "Claude CLI not found. Install with:\n"
                "  npm install -g @anthropic-ai/claude-code\n"
                "Then authenticate with:\n"
                "  claude auth"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude CLI check timed out")

    def _build_prompt_from_messages(self, messages: list) -> str:
        """
        Convert messages list to single formatted prompt.

        Format:
        <SYSTEM INSTRUCTIONS>
        {system_message}
        </SYSTEM INSTRUCTIONS>

        <CONVERSATION HISTORY>
        [USER]: {msg1}
        [ASSISTANT]: {msg2}
        </CONVERSATION HISTORY>

        <CURRENT MESSAGE>
        {last_user_message}
        </CURRENT MESSAGE>

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted prompt string
        """
        sections = []

        # Extract and format system message
        system_msg = None
        other_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                other_messages.append(msg)

        if system_msg:
            sections.append(
                f"<SYSTEM INSTRUCTIONS>\n{system_msg}\n</SYSTEM INSTRUCTIONS>"
            )

        # Format conversation history (all but last message)
        if len(other_messages) > 1:
            history = []
            for msg in other_messages[:-1]:
                role = msg["role"].upper()
                content = msg["content"]
                history.append(f"[{role}]: {content}")
            sections.append(
                f"<CONVERSATION HISTORY>\n" + "\n\n".join(history) +
                f"\n</CONVERSATION HISTORY>"
            )

        # Current message
        if other_messages:
            current = other_messages[-1]["content"]
            sections.append(
                f"<CURRENT MESSAGE>\n{current}\n</CURRENT MESSAGE>"
            )

        return "\n\n".join(sections)

    def _call_cli(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> dict:
        """
        Execute claude CLI and return parsed response.

        Args:
            prompt: Formatted prompt string
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Dict with 'content', 'input_tokens', 'output_tokens'

        Raises:
            RuntimeError: If CLI execution fails
        """
        cmd = [
            "claude",
            "-p",
            "--output-format", "json",
            "--model", self.cli_model_name,
        ]

        logger.debug(f"Executing CLI: {' '.join(cmd)}")
        logger.debug(f"Prompt length: {len(prompt)} chars, timeout: {self.cli_timeout}s")

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.cli_timeout,
                shell=False,  # Security: never use shell=True
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {error_msg}")

            # Parse JSON response
            try:
                response_data = json.loads(result.stdout)
                content = self._extract_content(response_data)
                input_tokens, output_tokens = self._extract_tokens(response_data)

                return {
                    "content": content,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            except json.JSONDecodeError as e:
                # Fallback: use raw stdout as content
                logger.warning(f"Failed to parse CLI JSON response: {e}")
                logger.warning("Using raw output as content")
                content = result.stdout
                # Estimate tokens (rough approximation: 4 chars ≈ 1 token)
                input_tokens = len(prompt) // 4
                output_tokens = len(content) // 4

                return {
                    "content": content,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }

        except subprocess.TimeoutExpired:
            logger.error(f"Claude CLI timeout after {self.cli_timeout}s")
            raise RuntimeError(
                f"Claude CLI timeout after {self.cli_timeout}s. "
                "Try increasing timeout in config or simplifying the prompt."
            )

    def _extract_content(self, json_response: dict) -> str:
        """
        Extract content from CLI JSON response.

        Args:
            json_response: Parsed JSON response from CLI

        Returns:
            Response content string
        """
        # Debug logging
        logger.debug(f"Extracting content from JSON response (type: {type(json_response)})")
        if isinstance(json_response, dict):
            logger.debug(f"JSON keys: {list(json_response.keys())}")
            if "result" in json_response:
                logger.debug(f"Found 'result' field (type: {type(json_response['result'])})")

        # Try result field first (Claude CLI standard format)
        if "result" in json_response:
            result = json_response["result"]
            if isinstance(result, str):
                logger.debug("Returning result field as content")
                return result

        # Try content field (Anthropic API style)
        if "content" in json_response:
            content = json_response["content"]
            # Handle list of content blocks
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    return content[0]["text"]
            # Handle direct string content
            if isinstance(content, str):
                return content

        # Fallback: try to find text anywhere in response
        if "text" in json_response:
            return json_response["text"]

        # Last resort: stringify the whole response
        logger.warning("Could not extract content from CLI response, using full JSON")
        return json.dumps(json_response)

    def _extract_tokens(self, json_response: dict) -> tuple[int, int]:
        """
        Extract token counts from CLI JSON response.

        Args:
            json_response: Parsed JSON response from CLI

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        try:
            # Try usage field first (Claude CLI standard format)
            if "usage" in json_response:
                usage = json_response["usage"]
                # Sum all input token types
                input_tokens = (
                    usage.get("input_tokens", 0) +
                    usage.get("cache_read_input_tokens", 0) +
                    usage.get("cache_creation_input_tokens", 0)
                )
                output_tokens = usage.get("output_tokens", 0)

                if input_tokens > 0 or output_tokens > 0:
                    return input_tokens, output_tokens

            # Try context_window structure (alternative format)
            if "context_window" in json_response:
                ctx = json_response["context_window"]
                input_tokens = ctx.get("total_input_tokens", 0)
                output_tokens = ctx.get("total_output_tokens", 0)

                if input_tokens > 0 and output_tokens > 0:
                    return input_tokens, output_tokens

            # Try usage structure (Anthropic API style)
            if "usage" in json_response:
                usage = json_response["usage"]
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

                if input_tokens > 0 and output_tokens > 0:
                    return input_tokens, output_tokens
        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"Failed to extract tokens from CLI response: {e}")

        # Fallback: estimate based on content length
        # 1 token ≈ 4 characters (rough approximation)
        content = self._extract_content(json_response)
        estimated_output = len(content) // 4
        estimated_input = 0  # Can't estimate without prompt reference

        logger.warning(
            f"Token extraction failed, estimating: "
            f"input={estimated_input}, output={estimated_output}"
        )

        return estimated_input, estimated_output

    def _call_api(
        self,
        messages: list,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AgentResponse:
        """
        Implement BaseAgent's abstract method using CLI subprocess.

        Args:
            messages: List of message dicts
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            AgentResponse with content and token counts (cost=0.0 for CLI)
        """
        # Check mock mode
        if self.config.mock_mode:
            logger.info("Mock mode enabled, returning mock response")
            return self.mock_response(messages[-1].get("content", ""))

        # Build prompt from messages
        prompt = self._build_prompt_from_messages(messages)

        try:
            # Call CLI
            result = self._call_cli(prompt, max_tokens, temperature)

            # Return AgentResponse (cost=0.0 for CLI models)
            return AgentResponse(
                content=result["content"],
                model=self.model_name,
                input_tokens=result["input_tokens"],
                output_tokens=result["output_tokens"],
                cost=0.0,  # CLI models have no per-token cost
                metadata={"cli": True, "model": self.cli_model_name}
            )

        except RuntimeError as e:
            # Return error response instead of crashing
            logger.error(f"CLI execution failed: {e}")
            return AgentResponse(
                content=f"[ERROR] Claude CLI failed: {str(e)}",
                model=self.model_name,
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                metadata={"error": str(e), "cli": True}
            )

    def chat_with_tools(
        self,
        message: str,
        tools: List[Dict[str, Any]],
        tool_executor: 'ToolExecutor',
        session_id: str,
        context: Optional[list] = None,
        max_turns: int = 5,
    ) -> AgentResponse:
        """
        Have a conversation with tool support.

        The agent can request tool calls by outputting structured JSON blocks.
        We parse these, execute the tools, and feed results back.

        Args:
            message: User message
            tools: List of available tool definitions
            tool_executor: ToolExecutor instance to execute tools
            session_id: Session ID (used as spawned_by for tool calls)
            context: Optional conversation history
            max_turns: Maximum tool use turns (prevents loops)

        Returns:
            Final AgentResponse after all tool calls resolved
        """
        from core import tools as tools_module

        # Build tool documentation for system prompt
        tool_docs = self._format_tool_docs(tools)

        # Create system message with tool instructions
        system_message = f"""You are an AI assistant with access to the following tools:

{tool_docs}

To use a tool, output a JSON block in this exact format:

```tool_use
{{
  "tool": "tool_name",
  "input": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
```

You can use multiple tools by outputting multiple ```tool_use blocks.
After tool results are provided, continue the conversation naturally.

IMPORTANT: Only use tools when necessary. For simple questions, just respond directly.
"""

        # Build messages list
        messages = []
        messages.append({"role": "system", "content": system_message})

        # Add context if provided
        if context:
            for ctx_msg in context:
                messages.append(ctx_msg)

        # Add current user message
        messages.append({"role": "user", "content": message})

        # Conversation loop with tool support
        turn_count = 0
        total_input_tokens = 0
        total_output_tokens = 0

        while turn_count < max_turns:
            turn_count += 1

            # Get agent response
            response = self._call_api(
                messages=messages,
                max_tokens=4096,
                temperature=0.7
            )

            total_input_tokens += response.input_tokens
            total_output_tokens += response.output_tokens

            # Check for tool use requests
            tool_calls = self._extract_tool_calls(response.content)

            if not tool_calls:
                # No more tool calls - return final response
                return AgentResponse(
                    content=response.content,
                    model=self.model_name,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    cost=0.0,
                    metadata={"cli": True, "tool_turns": turn_count}
                )

            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                tool_input = tool_call.get("input", {})

                logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

                result = tool_executor.execute(tool_name, tool_input, session_id)
                tool_results.append({
                    "tool": tool_name,
                    "result": result
                })

            # Add assistant message and tool results to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Format tool results for next turn
            tool_results_text = "\n\n".join([
                f"Tool: {tr['tool']}\nResult: {json.dumps(tr['result'], indent=2)}"
                for tr in tool_results
            ])

            messages.append({
                "role": "user",
                "content": f"<tool_results>\n{tool_results_text}\n</tool_results>"
            })

        # Max turns reached - return last response
        logger.warning(f"Tool conversation hit max_turns ({max_turns})")
        return AgentResponse(
            content=response.content + f"\n\n[Note: Reached maximum tool use turns ({max_turns})]",
            model=self.model_name,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cost=0.0,
            metadata={"cli": True, "tool_turns": turn_count, "max_turns_reached": True}
        )

    def _format_tool_docs(self, tools: List[Dict[str, Any]]) -> str:
        """Format tool definitions as documentation string."""
        docs = []
        for tool in tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "")
            schema = tool.get("input_schema", {})

            # Format schema
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            params_doc = []
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                req_marker = " (required)" if param_name in required else " (optional)"
                params_doc.append(f"  - {param_name}: {param_type}{req_marker} - {param_desc}")

            tool_doc = f"""
### {name}
{description}

Parameters:
{chr(10).join(params_doc) if params_doc else '  (no parameters)'}
"""
            docs.append(tool_doc)

        return "\n".join(docs)

    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract tool call requests from agent response.

        Looks for ```tool_use blocks with JSON tool requests.

        Returns:
            List of tool call dicts: [{"tool": "name", "input": {...}}, ...]
        """
        tool_calls = []

        # Find all ```tool_use blocks
        pattern = r'```tool_use\s*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                if "tool" in tool_call:
                    tool_calls.append(tool_call)
                else:
                    logger.warning(f"Tool call missing 'tool' field: {tool_call}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse tool_use block: {e}\nContent: {match}")

        return tool_calls
