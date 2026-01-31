"""WebSocket chat endpoint — spawns Claude CLI and streams responses."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sqlite3
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pathlib import Path

from ..config import settings
from ..prompt import assemble_system_prompt

router = APIRouter(tags=["chat"])
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sessions DB helpers (self-contained)
# ---------------------------------------------------------------------------

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS sessions (
    chat_id           INTEGER NOT NULL,
    name              TEXT    NOT NULL,
    user_id           INTEGER NOT NULL,
    claude_session_id TEXT    NOT NULL,
    model             TEXT    NOT NULL DEFAULT 'claude',
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        REAL    NOT NULL,
    last_active_at    REAL    NOT NULL,
    message_count     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, name)
)
"""


def _get_session_conn() -> sqlite3.Connection:
    db_path = settings.sessions_db
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def _get_or_create_session(
    chat_id: int, session_name: str
) -> dict:
    """Look up a session; create it if it doesn't exist."""
    conn = _get_session_conn()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE chat_id = ? AND name = ?",
            (chat_id, session_name),
        ).fetchone()

        if row:
            return {
                "chat_id": row["chat_id"],
                "name": row["name"],
                "user_id": row["user_id"],
                "claude_session_id": row["claude_session_id"],
                "model": row["model"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
                "last_active_at": row["last_active_at"],
                "message_count": row["message_count"],
            }

        # Auto-create the session
        now = time.time()
        session_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO sessions "
            "(chat_id, name, user_id, claude_session_id, model, is_active, "
            "created_at, last_active_at, message_count) "
            "VALUES (?, ?, 0, ?, 'claude', 1, ?, ?, 0)",
            (chat_id, session_name, session_id, now, now),
        )
        conn.commit()
        return {
            "chat_id": chat_id,
            "name": session_name,
            "user_id": 0,
            "claude_session_id": session_id,
            "model": "claude",
            "is_active": True,
            "created_at": now,
            "last_active_at": now,
            "message_count": 0,
        }
    finally:
        conn.close()


def _update_session_after_response(
    chat_id: int,
    session_name: str,
    new_session_id: str | None,
) -> None:
    """Bump last_active_at and message_count; optionally update session ID."""
    conn = _get_session_conn()
    try:
        now = time.time()
        if new_session_id:
            conn.execute(
                "UPDATE sessions SET last_active_at = ?, message_count = message_count + 1, "
                "claude_session_id = ? WHERE chat_id = ? AND name = ?",
                (now, new_session_id, chat_id, session_name),
            )
        else:
            conn.execute(
                "UPDATE sessions SET last_active_at = ?, message_count = message_count + 1 "
                "WHERE chat_id = ? AND name = ?",
                (now, chat_id, session_name),
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Claude process management
# ---------------------------------------------------------------------------

_active_processes: dict[str, asyncio.subprocess.Process] = {}


async def _kill_claude(proc: asyncio.subprocess.Process) -> None:
    """Send SIGTERM, wait up to 5 s, then SIGKILL if still alive."""
    if proc.returncode is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()


async def _spawn_and_stream(
    prompt: str,
    session: dict,
    websocket: WebSocket,
) -> None:
    """Spawn the claude CLI with --output-format stream-json and stream
    deltas back over the websocket.
    """
    session_id = session["claude_session_id"]
    model = session["model"]
    chat_id = session["chat_id"]
    session_name = session["name"]
    is_resume = session["message_count"] > 0
    interaction_start = time.time()

    # Usage tracking accumulators
    usage_model: str = model
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0
    usage_cache_creation: int = 0
    usage_cache_read: int = 0
    result_cost_usd: float | None = None
    result_num_turns: int = 0

    # Assemble system prompt
    try:
        system_prompt = assemble_system_prompt()
    except Exception:
        log.exception("Failed to assemble system prompt")
        system_prompt = ""

    # MCP config path
    mcp_config = Path(__file__).resolve().parent.parent / "mcp-config.json"

    # Build command
    cmd: list[str] = [
        settings.claude_cli_path,
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
        "--max-turns", str(settings.max_turns),
    ]

    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    if mcp_config.is_file():
        cmd.extend(["--mcp-config", str(mcp_config)])

    if model and model != "claude":
        if settings.allowed_models and model not in settings.allowed_models:
            log.warning("model %s not in allowed_models, falling back to %s", model, settings.subagent_model)
            model = settings.subagent_model
        cmd.extend(["--model", model])

    if is_resume:
        cmd.extend(["--resume", session_id])

    log.info("spawning claude: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=1024 * 1024,  # 1 MB — system prompt can produce large JSON lines
    )

    proc_key = f"{chat_id}:{session_name}"
    _active_processes[proc_key] = proc

    accumulated: list[str] = []
    result_text: str | None = None
    result_session_id: str = session_id
    saw_deltas = False

    try:
        assert proc.stdout is not None

        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                log.debug("non-json line from claude: %s", line)
                continue

            etype = event.get("type")

            if etype == "system":
                continue

            elif etype == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text:
                        saw_deltas = True
                        accumulated.append(text)
                        await websocket.send_json({
                            "type": "delta",
                            "text": text,
                        })

            elif etype == "assistant":
                message = event.get("message", {})
                # Extract usage data
                usage = message.get("usage", {})
                if usage:
                    usage_input_tokens += usage.get("input_tokens", 0)
                    usage_output_tokens += usage.get("output_tokens", 0)
                    usage_cache_creation += usage.get("cache_creation_input_tokens", 0)
                    usage_cache_read += usage.get("cache_read_input_tokens", 0)
                if message.get("model"):
                    usage_model = message["model"]
                for block in message.get("content", []):
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        if text and not saw_deltas:
                            accumulated.append(text)
                            await websocket.send_json({
                                "type": "delta",
                                "text": text,
                            })

            elif etype == "result":
                result_text = event.get("result", "")
                result_session_id = event.get("session_id", session_id)
                result_cost_usd = event.get("cost_usd")
                result_num_turns = event.get("num_turns", 0)

    except asyncio.CancelledError:
        await _kill_claude(proc)
        raise
    except WebSocketDisconnect:
        await _kill_claude(proc)
        raise

    # Wait for the process to finish
    await proc.wait()

    # Collect stderr
    stderr_bytes = b""
    if proc.stderr is not None:
        stderr_bytes = await proc.stderr.read()
    stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()

    if stderr_text:
        log.warning("claude stderr (exit=%s): %s", proc.returncode, stderr_text)

    # Unregister process
    _active_processes.pop(proc_key, None)

    # Check for errors
    if proc.returncode != 0:
        # If resume failed, reset session so next attempt starts fresh
        if is_resume:
            log.warning("resume failed for %s:%s, resetting session", chat_id, session_name)
            try:
                conn = _get_session_conn()
                conn.execute(
                    "UPDATE sessions SET message_count = 0, claude_session_id = ? "
                    "WHERE chat_id = ? AND name = ?",
                    (str(uuid.uuid4()), chat_id, session_name),
                )
                conn.commit()
                conn.close()
            except Exception:
                log.exception("Failed to reset session after resume failure")

        error_msg = f"claude exited with code {proc.returncode}"
        if stderr_text:
            error_msg += f": {stderr_text}"
        if is_resume:
            error_msg += " (session reset — try again)"
        await websocket.send_json({
            "type": "error",
            "message": error_msg,
        })
        return

    # Send final result
    final_text = result_text if result_text is not None else "".join(accumulated)
    await websocket.send_json({
        "type": "result",
        "text": final_text,
        "session_id": result_session_id,
    })

    # Update session metadata
    new_sid = result_session_id if result_session_id != session_id else None
    _update_session_after_response(chat_id, session_name, new_sid)

    # Record usage
    try:
        from .usage import record_usage
        record_usage(
            session_id=result_session_id,
            chat_id=chat_id,
            session_name=session_name,
            model=usage_model,
            input_tokens=usage_input_tokens,
            output_tokens=usage_output_tokens,
            cache_creation_tokens=usage_cache_creation,
            cache_read_tokens=usage_cache_read,
            cost_usd=result_cost_usd,
            num_turns=result_num_turns,
            source="chat",
            started_at=interaction_start,
            completed_at=time.time(),
        )
    except Exception:
        log.exception("Failed to record usage")


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket chat endpoint.

    Accepts JSON messages:
        {"session_name": "default", "chat_id": 0, "message": "hello"}

    Streams back:
        {"type": "delta", "text": "..."}
        {"type": "result", "text": "...", "session_id": "..."}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    log.info("WebSocket connected")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            message = data.get("message", "")
            session_name = data.get("session_name", "default")
            chat_id = data.get("chat_id", 0)

            if not message:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty message",
                })
                continue

            # Look up or create the session
            session = _get_or_create_session(chat_id, session_name)

            # Spawn Claude and stream
            try:
                await _spawn_and_stream(message, session, websocket)
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                log.exception("Error in spawn_and_stream")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(exc),
                    })
                except Exception:
                    pass

    except WebSocketDisconnect:
        log.info("WebSocket disconnected")
