from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from dataclasses import dataclass
from typing import Callable, Awaitable

from herald.config import Config

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ClaudeError(Exception):
    """Non-zero exit from the claude CLI."""


class RateLimitError(Exception):
    """Claude API rate-limit (429) hit."""


class SessionNotFoundError(Exception):
    """Requested session does not exist."""


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class ClaudeResult:
    text: str
    session_id: str


# ---------------------------------------------------------------------------
# Active-process registry (keyed by Telegram chat_id)
# ---------------------------------------------------------------------------

_active_processes: dict[int, asyncio.subprocess.Process] = {}


def register_process(chat_id: int, proc: asyncio.subprocess.Process) -> None:
    _active_processes[chat_id] = proc


def unregister_process(chat_id: int) -> None:
    _active_processes.pop(chat_id, None)


async def kill_process(chat_id: int) -> None:
    """Kill the active process for *chat_id* (if any)."""
    proc = _active_processes.get(chat_id)
    if proc is None:
        return
    await kill_claude(proc)
    unregister_process(chat_id)


# ---------------------------------------------------------------------------
# Graceful kill helper
# ---------------------------------------------------------------------------

async def kill_claude(proc: asyncio.subprocess.Process) -> None:
    """Send SIGTERM, wait up to 5 s, then SIGKILL if still alive."""
    if proc.returncode is not None:
        return  # already exited

    try:
        proc.send_signal(signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        try:
            proc.kill()  # SIGKILL
        except ProcessLookupError:
            pass
        await proc.wait()


# ---------------------------------------------------------------------------
# Main spawner
# ---------------------------------------------------------------------------

async def spawn_claude(
    prompt: str,
    session_id: str,
    resume: bool,
    config: Config,
    on_delta: Callable[[str], Awaitable[None]] | None = None,
    model_name: str | None = None,
    system_prompt: str | None = None,
) -> ClaudeResult:
    """Spawn the ``claude`` CLI with ``--output-format stream-json`` and parse
    the streaming output, calling *on_delta* for every incremental text chunk.
    """

    # -- build command ---------------------------------------------------------
    cmd: list[str] = [
        config.claude_cli_path,
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
        "--max-turns", str(config.max_turns),
    ]

    if model_name:
        cmd.extend(["--model", model_name])

    # MCP config — gives Milo access to homestead tools (tasks, proposals, lore, etc.)
    if config.mcp_config_path:
        cmd.extend(["--mcp-config", config.mcp_config_path])

    if resume:
        # Resume an existing session (--resume takes session ID as its value)
        cmd.extend(["--resume", session_id])
    else:
        # New conversation — use assembled system prompt from lore files
        effective_prompt = system_prompt or config.system_prompt
        cmd.extend(["--system-prompt", effective_prompt])

    log.info("spawning claude: %s", " ".join(cmd))

    # -- clean environment: strip Claude Code SDK vars that cause exit code 1 --
    clean_env = {
        k: v for k, v in os.environ.items()
        if not k.startswith("CLAUDECODE") and not k.startswith("CLAUDE_CODE")
            and k != "CLAUDE_AGENT_SDK_VERSION"
    }

    # -- spawn -----------------------------------------------------------------
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=clean_env,
    )

    # -- parse stream-json -----------------------------------------------------
    accumulated: list[str] = []
    saw_deltas = False
    result_text: str | None = None
    result_session_id: str = session_id

    raw_lines_seen: list[str] = []

    async def _read_stdout() -> None:
        nonlocal saw_deltas, result_text, result_session_id
        assert proc.stdout is not None

        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            raw_lines_seen.append(line[:200])

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                log.debug("non-json line from claude: %s", line)
                continue

            etype = event.get("type")

            if etype == "system":
                # init / info events -- ignore
                continue

            elif etype == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        saw_deltas = True
                        accumulated.append(text)
                        if on_delta is not None:
                            await on_delta(text)

            elif etype == "assistant":
                # Full message block -- extract text content blocks.
                # Only forward via on_delta when we haven't already seen
                # incremental deltas (avoids duplicating output).
                message = event.get("message", {})
                for block in message.get("content", []):
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        if text and not saw_deltas:
                            accumulated.append(text)
                            if on_delta is not None:
                                await on_delta(text)

            elif etype == "result":
                result_text = event.get("result", "")
                result_session_id = event.get("session_id", session_id)

    # -- drive stdout reader with timeout --------------------------------------
    try:
        await asyncio.wait_for(_read_stdout(), timeout=config.claude_timeout_s)
    except asyncio.TimeoutError:
        log.warning("claude timed out after %ss – killing", config.claude_timeout_s)
        await kill_claude(proc)
        raise ClaudeError(
            f"claude process timed out after {config.claude_timeout_s}s"
        )

    # -- wait for the process to finish ----------------------------------------
    await proc.wait()

    # -- collect stderr --------------------------------------------------------
    stderr_bytes = b""
    if proc.stderr is not None:
        stderr_bytes = await proc.stderr.read()
    stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

    if stderr_text:
        log.warning("claude stderr (exit=%s): %s", proc.returncode, stderr_text)

    log.info("claude done: exit=%s stdout_chunks=%d stderr_len=%d resume=%s raw_lines=%d",
             proc.returncode, len(accumulated), len(stderr_text), resume, len(raw_lines_seen))

    # -- check for errors ------------------------------------------------------
    if proc.returncode != 0:
        log.warning("claude failed: exit=%s stderr=%r accumulated=%d resume=%s",
                     proc.returncode, stderr_text[:500] if stderr_text else "(empty)", len(accumulated), resume)
        for i, rl in enumerate(raw_lines_seen[:5]):
            log.warning("  stdout[%d]: %s", i, rl)
        stderr_lower = stderr_text.lower()

        if "rate limit" in stderr_lower or "429" in stderr_lower:
            raise RateLimitError(stderr_text or "Rate limited by Claude API")

        if "session" in stderr_lower and "not found" in stderr_lower:
            raise SessionNotFoundError(stderr_text)

        # Exit code 1 with no stderr during resume is almost always a stale
        # session — surface it as SessionNotFoundError so callers auto-rotate.
        if proc.returncode == 1 and not stderr_text and resume:
            log.warning("claude exit 1 with empty stderr during resume — treating as stale session")
            raise SessionNotFoundError("session likely expired (exit 1, no stderr)")

        detail = stderr_text or "no error output from CLI"
        raise ClaudeError(
            f"claude exited with code {proc.returncode}: {detail}"
        )

    # -- build result ----------------------------------------------------------
    final_text = result_text if result_text is not None else "".join(accumulated)

    return ClaudeResult(text=final_text, session_id=result_session_id)
