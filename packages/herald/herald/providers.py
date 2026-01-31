from __future__ import annotations

import json
import logging
import os
import time
from typing import Callable, Awaitable

import httpx

from herald.config import Config
from herald.claude import spawn_claude, ClaudeResult
from herald.prompt import assemble_system_prompt
from herald.sessions import SessionMeta

log = logging.getLogger(__name__)

_MANOR_API_URL = os.environ.get("MANOR_API_URL", "http://localhost:8700")

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


async def _report_usage(result: ClaudeResult, session: SessionMeta, started_at: float) -> None:
    """POST usage data to Manor API (best-effort)."""
    if result.input_tokens == 0 and result.output_tokens == 0:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{_MANOR_API_URL}/api/usage", json={
                "session_id": result.session_id,
                "chat_id": session.chat_id,
                "session_name": session.name,
                "model": result.model or session.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_creation_tokens": result.cache_creation_tokens,
                "cache_read_tokens": result.cache_read_tokens,
                "cost_usd": result.cost_usd,
                "num_turns": result.num_turns,
                "source": "herald",
                "started_at": started_at,
            })
    except Exception:
        log.warning("Failed to report usage to Manor API", exc_info=True)


async def dispatch_message(
    prompt: str,
    session: SessionMeta,
    config: Config,
    on_delta: Callable[[str], Awaitable[None]] | None = None,
) -> ClaudeResult:
    """Route a message to the right model backend."""
    model = session.model
    system_prompt = _get_system_prompt(config)
    started_at = time.time()

    if model in _CLI_MODELS:
        result = await spawn_claude(
            prompt,
            session.claude_session_id,
            session.message_count > 0,
            config,
            on_delta,
            model_name=_CLI_MODELS.get(model),
            system_prompt=system_prompt,
            chat_id=session.chat_id,
        )
    elif model == "grok":
        result = await _call_xai(prompt, session, config, on_delta, system_prompt)
    else:
        # Fallback: try Claude CLI default
        log.warning("Unknown model %r, falling back to claude CLI default", model)
        result = await spawn_claude(
            prompt,
            session.claude_session_id,
            session.message_count > 0,
            config,
            on_delta,
            system_prompt=system_prompt,
            chat_id=session.chat_id,
        )

    # Record usage for all providers
    try:
        await _report_usage(result, session, started_at)
    except Exception as exc:
        log.warning("Usage reporting failed: %s", exc)

    return result


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
