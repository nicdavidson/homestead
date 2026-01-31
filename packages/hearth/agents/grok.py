"""
Hearth Agents - Grok (xAI)
The cheap, always-on worker. Does the grind.
"""

import json
from typing import Optional
import httpx

from core import Config, get_config
from .base import BaseAgent, AgentResponse


class GrokAgent(BaseAgent):
    """
    Grok agent for cheap, always-on work.
    
    Good at:
    - Simple tasks
    - Parallel research (swarms)
    - Quick lookups
    - HA commands
    
    Not as good at:
    - Deep personality
    - Complex reasoning
    - Creative writing
    """
    
    BASE_URL = "https://api.x.ai/v1"
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.api_key = self.config.xai_key
    
    @property
    def model_name(self) -> str:
        return self.config.grok_model
    
    @property
    def model_tier(self) -> str:
        return "grok"
    
    def _call_api(
        self,
        messages: list,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AgentResponse:
        """Make API call to xAI."""
        if self.config.mock_mode:
            return self.mock_response(messages[-1]["content"])
        
        if not self.api_key:
            raise ValueError("xAI API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
        
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = self.costs.calculate_cost("grok", input_tokens, output_tokens)
        
        return AgentResponse(
            content=content,
            model=self.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
    
    def classify_task(self, task_description: str) -> dict:
        """
        Classify a task's complexity for routing.
        
        Returns dict with:
        - complexity: simple, medium, complex
        - score: 1-5
        - can_handle: bool
        - suggested_action: str
        """
        prompt = f"""Classify this task for routing:

TASK: {task_description}

Respond in JSON only:
{{
    "complexity": "simple" | "medium" | "complex",
    "score": 1-5,
    "can_handle": true/false,
    "reasoning": "brief explanation",
    "suggested_action": "what to do"
}}

Guidelines:
- simple (1-2): status checks, toggles, quick lookups
- medium (3): summaries, research, analysis
- complex (4-5): coding, deep thinking, creative work

You (Grok) handle simple and most medium tasks.
Escalate complex to Sonnet."""

        response = self.chat(prompt, include_identity=False, max_tokens=256, temperature=0.3)
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            result["raw_response"] = response
            return result
        except (json.JSONDecodeError, IndexError):
            return {
                "complexity": "medium",
                "score": 3,
                "can_handle": False,
                "reasoning": "Failed to parse, defaulting to escalation",
                "suggested_action": "Escalate to Sonnet"
            }
    
    def quick_action(self, action: str) -> str:
        """
        Execute a simple action and return result.
        For status checks, simple commands, etc.
        """
        prompt = f"""Execute this simple action and respond concisely:

ACTION: {action}

Keep response brief (1-3 sentences unless more detail is needed).
If you can't complete it, say why briefly."""

        response = self.chat(prompt, max_tokens=256)
        return response.content
    
    def research(self, query: str) -> str:
        """
        Do quick research on a topic.
        Returns summary suitable for synthesis.
        """
        prompt = f"""Research this topic and provide a concise summary:

QUERY: {query}

Provide:
1. Key facts (bullet points)
2. Notable sources if mentioned
3. Any gaps or uncertainties

Keep it factual and brief. This will be synthesized with other research."""

        response = self.chat(prompt, max_tokens=1024)
        return response.content
