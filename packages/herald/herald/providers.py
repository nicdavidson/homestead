from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable

from herald.config import Config
from herald.claude import spawn_claude, ClaudeResult
from herald.prompt import assemble_system_prompt
from herald.sessions import SessionMeta

log = logging.getLogger(__name__)

# Model -> Claude CLI model name mapping
_CLI_MODELS = {
    "claude": None,  # default model
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20251101",
}

# Cache assembled prompt (rebuilt per spawn, but avoid doing IO every delta)
_cached_prompt: str | None = None
_cached_prompt_config_id: int | None = None


def _get_system_prompt(config: Config) -> str:
    global _cached_prompt, _cached_prompt_config_id
    cfg_id = id(config)
    if _cached_prompt is None or _cached_prompt_config_id != cfg_id:
        _cached_prompt = assemble_system_prompt(config)
        _cached_prompt_config_id = cfg_id
    return _cached_prompt


def refresh_prompt(config: Config) -> str:
    """Force-rebuild the system prompt (e.g. after skill/lore changes)."""
    global _cached_prompt, _cached_prompt_config_id
    _cached_prompt = assemble_system_prompt(config)
    _cached_prompt_config_id = id(config)
    return _cached_prompt


async def dispatch_message(
    prompt: str,
    session: SessionMeta,
    config: Config,
    on_delta: Callable[[str], Awaitable[None]] | None = None,
) -> ClaudeResult:
    """Route a message to the right model backend."""
    model = session.model
    system_prompt = _get_system_prompt(config)

    if model in _CLI_MODELS:
        return await spawn_claude(
            prompt,
            session.claude_session_id,
            session.message_count > 0,
            config,
            on_delta,
            model_name=_CLI_MODELS.get(model),
            system_prompt=system_prompt,
        )

    if model == "grok":
        return await _call_xai(prompt, session, config, on_delta, system_prompt)

    # Fallback: try Claude CLI default
    log.warning("Unknown model %r, falling back to claude CLI default", model)
    return await spawn_claude(
        prompt,
        session.claude_session_id,
        session.message_count > 0,
        config,
        on_delta,
        system_prompt=system_prompt,
    )


async def _call_xai(
    prompt: str,
    session: SessionMeta,
    config: Config,
    on_delta: Callable[[str], Awaitable[None]] | None = None,
    system_prompt: str = "",
) -> ClaudeResult:
    """Call xAI (Grok) API directly via httpx."""
    if not config.xai_api_key:
        raise RuntimeError("XAI_API_KEY not set — cannot use grok model")

    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx is required for grok model: pip install httpx")

    headers = {
        "Authorization": f"Bearer {config.xai_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "grok-3",
        "messages": [
            {"role": "system", "content": system_prompt or config.system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": True,
    }

    accumulated: list[str] = []

    async with httpx.AsyncClient(timeout=config.claude_timeout_s) as client:
        async with client.stream(
            "POST",
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                    delta = event.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        accumulated.append(text)
                        if on_delta is not None:
                            await on_delta(text)
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue

    return ClaudeResult(
        text="".join(accumulated),
        session_id=session.claude_session_id,
    )
