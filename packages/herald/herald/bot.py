from __future__ import annotations

import asyncio
import html
import logging
import os
import re
import sys
import time
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from herald.config import Config
from herald.auth import is_authorized
from herald.sessions import SessionManager
from herald.queue import MessageQueue, QueuedMessage
from herald.providers import dispatch_message
from herald.voice import handle_voice
from herald.middleware import RateLimitMiddleware, LoggingMiddleware
from herald.claude import (
    kill_process,
    ClaudeResult,
    RateLimitError,
    SessionNotFoundError,
    ClaudeError,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Usage reporting
# ---------------------------------------------------------------------------

_MANOR_API_URL = os.environ.get("MANOR_API_URL", "http://localhost:8700")


async def _report_usage(result: ClaudeResult, session_name: str, chat_id: int, started_at: float) -> None:
    """POST usage data to Manor API in the background (best-effort)."""
    if result.input_tokens == 0 and result.output_tokens == 0:
        return  # nothing to report
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{_MANOR_API_URL}/api/usage", json={
                "session_id": result.session_id,
                "chat_id": chat_id,
                "session_name": session_name,
                "model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_creation_tokens": result.cache_creation_tokens,
                "cache_read_tokens": result.cache_read_tokens,
                "cost_usd": result.cost_usd,
                "num_turns": result.num_turns,
                "source": "herald",
                "started_at": started_at,
            })
    except Exception as exc:
        log.warning("chat=%d usage reporting failed: %s", chat_id, exc)


# ---------------------------------------------------------------------------
# Markdown -> Telegram HTML
# ---------------------------------------------------------------------------

def md_to_telegram_html(text: str) -> str:
    """Convert a subset of Markdown to Telegram-supported HTML."""
    try:
        # First escape all HTML to prevent injection
        escaped = html.escape(text)

        # Replace code blocks (must come before inline code)
        def _replace_code_block(m: re.Match) -> str:
            lang = m.group(1) or ""
            code = html.unescape(m.group(2)).strip("\n")
            # Code is already escaped from the initial escape, just wrap it
            if lang:
                return f'<pre><code class="language-{lang}">{code}</code></pre>'
            return f"<pre><code>{code}</code></pre>"

        result = re.sub(
            r"```(\w*)\n(.*?)```", _replace_code_block, escaped, flags=re.DOTALL
        )

        # Replace inline code
        def _replace_inline_code(m: re.Match) -> str:
            # Code is already escaped from initial escape, just wrap it
            code = m.group(1)
            return f"<code>{code}</code>"

        result = re.sub(r"`([^`]+)`", _replace_inline_code, result)

        # Replace bold (must come before italic to handle ***)
        result = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result)

        # Replace italic (avoid matching **)
        result = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", result)

        # Strip any remaining unsupported HTML tags that might have leaked through
        # Telegram only supports: b, i, code, pre, a, u, s, strike, del
        # Remove any <mark>, <span>, <div>, etc.
        result = re.sub(r'<(?!/?(?:b|i|code|pre|a|u|s|strike|del|strong|em)\b)[^>]+>', '', result)

        return result
    except Exception:
        log.debug("md_to_telegram_html conversion failed", exc_info=True)
        # Fallback: just escape everything
        return html.escape(text)


# ---------------------------------------------------------------------------
# Message splitting
# ---------------------------------------------------------------------------

def split_message(text: str, max_len: int = 4000) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to find a good break point (newline, then space)
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_len)
        # If still no break point found, force split at max_len
        if split_at == -1 or split_at == 0:
            split_at = max_len
        chunks.append(text[:split_at])
        # Remove the chunk and strip leading whitespace
        text = text[split_at:].lstrip("\n ")
    return chunks


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------

class AuthMiddleware(BaseMiddleware):
    def __init__(self, config: Config):
        self.config = config

    async def __call__(self, handler, event: types.Message, data: dict):
        if not is_authorized(event.from_user.id, self.config):
            await event.answer("This bot is private.")
            return
        return await handler(event, data)


# ---------------------------------------------------------------------------
# Outbox polling
# ---------------------------------------------------------------------------

async def poll_outbox(bot: Bot, config: Config) -> None:
    """Background task: deliver messages from the shared outbox."""
    outbox_db = Path(config.homestead_data_dir).expanduser() / "outbox.db"

    # Add common package to sys.path if needed
    common_path = Path(__file__).resolve().parent.parent.parent / "common"
    if str(common_path) not in sys.path:
        sys.path.insert(0, str(common_path))

    try:
        from common.outbox import get_pending, mark_sent, mark_failed
        from common.models import format_agent_message
    except ImportError:
        log.warning("common package not importable, outbox polling disabled")
        return

    while True:
        try:
            messages = get_pending(str(outbox_db))
            for msg in messages:
                try:
                    formatted = format_agent_message(msg.agent_name, msg.message)

                    # Parse inline keyboard if present
                    reply_markup = None
                    if "__KEYBOARD__" in formatted:
                        parts = formatted.split("__KEYBOARD__", 1)
                        formatted = parts[0].strip()
                        if len(parts) > 1:
                            try:
                                import json
                                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                                kbd = json.loads(parts[1])
                                buttons = [[InlineKeyboardButton(text=b["text"], callback_data=b.get("callback_data", "")) for b in row] for row in kbd.get("inline_keyboard", [])]
                                reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                            except Exception:
                                log.warning("Failed to parse keyboard", exc_info=True)

                    await bot.send_message(
                        msg.chat_id, formatted, parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                    mark_sent(str(outbox_db), msg.id)
                    log.info("outbox: delivered msg %d to chat %d (%s)", msg.id, msg.chat_id, msg.agent_name)
                except Exception:
                    log.exception("outbox: failed to deliver msg %d to chat %d", msg.id, msg.chat_id)
                    mark_failed(str(outbox_db), msg.id)
        except Exception as exc:
            log.debug("outbox: poll error (DB may not exist yet): %s", exc)
        await asyncio.sleep(config.outbox_poll_interval_s)


# ---------------------------------------------------------------------------
# Queue processor
# ---------------------------------------------------------------------------

async def process_queue(
    bot: Bot,
    chat_id: int,
    config: Config,
    sessions: SessionManager,
    queue: MessageQueue,
) -> None:
    """Drain the message queue for *chat_id*, processing one item at a time."""
    while True:
        msg = queue.dequeue(chat_id)
        if msg is None:
            queue.mark_idle(chat_id)
            return

        queue.mark_active(chat_id)

        # Session management
        session = sessions.get_active(chat_id)
        if session and sessions.is_stale(session):
            log.info("chat=%d session %s is stale, rotating", chat_id, session.name)
            session = sessions.rotate(chat_id, msg.user_id, session.name, session.model)
        if session is None:
            session = sessions.create(chat_id, msg.user_id)

        resume = session.message_count > 0
        sessions.touch(session)

        await bot.send_chat_action(chat_id, ChatAction.TYPING)

        typing_task: asyncio.Task | None = None

        async def _keep_typing() -> None:
            try:
                while True:
                    await asyncio.sleep(4.0)
                    await bot.send_chat_action(chat_id, ChatAction.TYPING)
            except asyncio.CancelledError:
                pass

        accumulated = ""
        last_edit_time = 0.0
        sent_message_id: int | None = None

        async def on_delta(text: str) -> None:
            nonlocal accumulated, last_edit_time, sent_message_id, typing_task
            accumulated += text
            now = time.time()
            if now - last_edit_time >= config.streaming_interval_s and accumulated.strip():
                if sent_message_id is None:
                    # Keep typing indicator active during streaming
                    try:
                        sent = await bot.send_message(
                            chat_id,
                            md_to_telegram_html(accumulated),
                            parse_mode=ParseMode.HTML,
                        )
                        sent_message_id = sent.message_id
                    except Exception as exc:
                        log.warning("chat=%d stream send_message failed: %s", chat_id, exc)
                else:
                    try:
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=sent_message_id,
                            text=md_to_telegram_html(accumulated),
                            parse_mode=ParseMode.HTML,
                        )
                    except Exception as exc:
                        log.debug("chat=%d stream edit failed: %s", chat_id, exc)
                last_edit_time = now

        try:
            typing_task = asyncio.create_task(_keep_typing())
            spawn_started_at = time.time()

            log.info(
                "chat=%s user=%s spawning %s (session=%s/%s resume=%s)",
                chat_id, msg.user_id, session.model,
                session.name, session.claude_session_id[:8], resume,
            )

            result = await dispatch_message(
                msg.text, session, config, on_delta
            )

            if typing_task is not None:
                typing_task.cancel()
                typing_task = None

            log.info("chat=%s claude responded (%d chars)", chat_id, len(result.text))

            # Report usage to Manor API (fire-and-forget)
            asyncio.create_task(_report_usage(result, session.name, chat_id, spawn_started_at))

            if result.session_id and result.session_id != session.claude_session_id:
                sessions.update_session_id(session, result.session_id)

            final_html = md_to_telegram_html(result.text if result.text else accumulated)
            parts = split_message(final_html)

            if sent_message_id is not None:
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=sent_message_id,
                        text=parts[0] or "Done.",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception as exc:
                    log.warning("chat=%d final edit_message failed: %s", chat_id, exc)
            else:
                try:
                    await bot.send_message(
                        chat_id, parts[0] or "Done.", parse_mode=ParseMode.HTML
                    )
                except Exception as exc:
                    log.warning("chat=%d final send_message failed: %s", chat_id, exc)

            for part in parts[1:]:
                await bot.send_message(chat_id, part, parse_mode=ParseMode.HTML)

        except RateLimitError:
            log.warning("chat=%s rate limited", chat_id)
            if typing_task is not None:
                typing_task.cancel()
            await bot.send_message(chat_id, "Rate limited, try again in a moment.")

        except SessionNotFoundError:
            log.warning("chat=%s session not found, rotating and retrying", chat_id)
            if typing_task is not None:
                typing_task.cancel()
                typing_task = None
            session = sessions.rotate(chat_id, msg.user_id, session.name, session.model)

            # Auto-retry with fresh session
            try:
                typing_task = asyncio.create_task(_keep_typing())
                retry_started_at = time.time()
                result = await dispatch_message(msg.text, session, config, on_delta)
                if typing_task is not None:
                    typing_task.cancel()
                    typing_task = None
                asyncio.create_task(_report_usage(result, session.name, chat_id, retry_started_at))
                if result.session_id and result.session_id != session.claude_session_id:
                    sessions.update_session_id(session, result.session_id)
                final_html = md_to_telegram_html(result.text if result.text else accumulated)
                parts = split_message(final_html)
                prefix = "<i>↻ new session</i>\n\n"
                first_part = prefix + (parts[0] or "Done.")
                if sent_message_id is not None:
                    try:
                        await bot.edit_message_text(
                            chat_id=chat_id, message_id=sent_message_id,
                            text=first_part, parse_mode=ParseMode.HTML,
                        )
                    except Exception as exc:
                        log.warning("chat=%d retry edit failed, sending new: %s", chat_id, exc)
                        await bot.send_message(chat_id, first_part, parse_mode=ParseMode.HTML)
                else:
                    await bot.send_message(chat_id, first_part, parse_mode=ParseMode.HTML)
                for part in parts[1:]:
                    await bot.send_message(chat_id, part, parse_mode=ParseMode.HTML)
            except Exception as retry_err:
                log.error("chat=%s retry after rotate also failed: %s", chat_id, retry_err)
                if typing_task is not None:
                    typing_task.cancel()
                await bot.send_message(chat_id, f"Error: {retry_err}")

        except ClaudeError as e:
            log.error("chat=%s claude error: %s", chat_id, e)
            if typing_task is not None:
                typing_task.cancel()
            await bot.send_message(chat_id, f"Error: {e}")

        except Exception as e:
            log.exception("chat=%s unexpected error: %s", chat_id, e)
            if typing_task is not None:
                typing_task.cancel()
            try:
                await bot.send_message(chat_id, f"Unexpected error: {e}")
            except Exception as send_exc:
                log.error("chat=%d failed to send error message: %s", chat_id, send_exc)

    queue.mark_idle(chat_id)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_bot(
    config: Config,
    sessions: SessionManager,
    queue: MessageQueue,
    watchtower=None,
) -> tuple[Bot, Dispatcher]:
    """Create aiogram bot and dispatcher, register handlers."""
    bot = Bot(token=config.telegram_bot_token)
    dp = Dispatcher()

    dp.message.middleware(AuthMiddleware(config))
    dp.message.middleware(RateLimitMiddleware())
    dp.message.middleware(LoggingMiddleware())

    # -- Commands --------------------------------------------------------

    @dp.message(Command("new"))
    async def cmd_new(message: types.Message):
        session = sessions.get_active(message.chat.id)
        model = session.model if session else "claude"
        name = session.name if session else "default"
        sessions.rotate(message.chat.id, message.from_user.id, name, model)
        await message.answer(f"Fresh conversation started ({name}/{model}).")

    @dp.message(Command("status"))
    async def cmd_status(message: types.Message):
        session = sessions.get_active(message.chat.id)
        if not session:
            await message.answer("No active session.")
            return
        age_hours = (time.time() - session.created_at) / 3600
        await message.answer(
            f"Session: {session.name}\n"
            f"Model: {session.model}\n"
            f"ID: {session.claude_session_id[:8]}...\n"
            f"Messages: {session.message_count}\n"
            f"Age: {age_hours:.1f}h"
        )

    @dp.message(Command("cancel"))
    async def cmd_cancel(message: types.Message):
        await kill_process(message.chat.id)
        queue.clear(message.chat.id)
        queue.mark_idle(message.chat.id)
        await message.answer("Cancelled.")

    @dp.message(Command("session"))
    async def cmd_session(message: types.Message):
        args = (message.text or "").split()[1:]  # skip /session

        if not args:
            # Show current session + list all
            all_sessions = sessions.list_sessions(message.chat.id)
            if not all_sessions:
                await message.answer("No sessions. Send a message to start one.")
                return
            lines = []
            for s in all_sessions:
                marker = "\u2192 " if s.is_active else "  "
                lines.append(f"{marker}{s.name} ({s.model}) - {s.message_count} msgs")
            await message.answer("Sessions:\n" + "\n".join(lines))
            return

        name = args[0].lower()
        model = args[1].lower() if len(args) > 1 else None

        # Validate model if provided
        if model and model not in config.model_allowlist:
            await message.answer(
                f"Unknown model: {model}\nAllowed: {', '.join(config.model_allowlist)}"
            )
            return

        # Try to switch to existing session
        existing = sessions.get_by_name(message.chat.id, name)
        if existing:
            if model and model != existing.model:
                sessions.set_model(message.chat.id, name, model)
                existing.model = model
            sessions.switch(message.chat.id, name)
            await message.answer(f"Switched to session: {name} ({existing.model})")
        else:
            # Create new session
            model = model or "claude"
            sessions.create(message.chat.id, message.from_user.id, name, model)
            await message.answer(f"Created session: {name} ({model})")

    @dp.message(Command("sessions"))
    async def cmd_sessions(message: types.Message):
        all_sessions = sessions.list_sessions(message.chat.id)
        if not all_sessions:
            await message.answer("No sessions.")
            return
        lines = []
        for s in all_sessions:
            marker = "\u2192 " if s.is_active else "  "
            age = (time.time() - s.created_at) / 3600
            lines.append(f"{marker}{s.name} ({s.model}) - {s.message_count} msgs, {age:.1f}h old")
        await message.answer("Sessions:\n" + "\n".join(lines))

    @dp.message(Command("model"))
    async def cmd_model(message: types.Message):
        args = (message.text or "").split()[1:]
        session = sessions.get_active(message.chat.id)

        if not args:
            if session:
                await message.answer(
                    f"Current model: {session.model}\n"
                    f"Available: {', '.join(config.model_allowlist)}"
                )
            else:
                await message.answer(f"Available models: {', '.join(config.model_allowlist)}")
            return

        model = args[0].lower()
        if model not in config.model_allowlist:
            await message.answer(
                f"Unknown model: {model}\nAllowed: {', '.join(config.model_allowlist)}"
            )
            return

        if session:
            sessions.set_model(message.chat.id, session.name, model)
            # Create new CLI session for the new model (contexts aren't shared)
            sessions.rotate(message.chat.id, message.from_user.id, session.name, model)
            await message.answer(f"Model changed to: {model} (new conversation)")
        else:
            sessions.create(message.chat.id, message.from_user.id, "default", model)
            await message.answer(f"Created session with model: {model}")

    @dp.message(Command("logs"))
    async def cmd_logs(message: types.Message):
        if watchtower is None:
            await message.answer("Watchtower not available.")
            return

        args = (message.text or "").split()[1:]
        hours = float(args[0]) if args else 24

        try:
            summary = watchtower.summary(hours)
            if not summary:
                await message.answer(f"No logs in the last {hours}h.")
                return

            lines = [f"Log summary (last {hours}h):"]
            for source, levels in sorted(summary.items()):
                parts = [f"{lvl}: {cnt}" for lvl, cnt in sorted(levels.items())]
                lines.append(f"  {source}: {', '.join(parts)}")

            errors = watchtower.errors_since(hours)
            if errors:
                lines.append(f"\nRecent errors ({len(errors)}):")
                for e in errors[:5]:
                    lines.append(f"  [{e.source}] {e.message[:80]}")

            await message.answer("\n".join(lines))
        except Exception as e:
            await message.answer(f"Error querying logs: {e}")

    @dp.message(Command("task"))
    async def cmd_task(message: types.Message):
        """Create or list tasks. Usage: /task [title] or /task list [status]"""
        args = (message.text or "").split(None, 2)  # /task, subcommand, rest

        # Import steward store
        try:
            steward_db = Path(config.homestead_data_dir).expanduser() / "steward" / "tasks.db"
            # Inline SQLite access (avoid coupling to steward package)
            import sqlite3, json, uuid, time as _time

            conn = sqlite3.connect(str(steward_db))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            # Ensure table
            conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending', priority TEXT NOT NULL DEFAULT 'normal',
                assignee TEXT DEFAULT 'auto', blockers_json TEXT DEFAULT '[]',
                depends_on_json TEXT DEFAULT '[]', created_at REAL NOT NULL,
                updated_at REAL NOT NULL, completed_at REAL, tags_json TEXT DEFAULT '[]',
                notes_json TEXT DEFAULT '[]', source TEXT DEFAULT ''
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status)")
            conn.commit()
        except Exception as e:
            await message.answer(f"Task system error: {e}")
            return

        if len(args) < 2 or args[1] == "list":
            # List tasks
            status_filter = args[2] if len(args) > 2 else None
            query = "SELECT id, title, status, priority FROM tasks"
            params = []
            if status_filter:
                query += " WHERE status = ?"
                params.append(status_filter)
            query += " ORDER BY CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, created_at DESC LIMIT 15"

            rows = conn.execute(query, params).fetchall()
            conn.close()

            if not rows:
                await message.answer("No tasks found.")
                return

            status_icons = {"pending": "\u23f3", "in_progress": "\U0001f504", "blocked": "\U0001f6ab", "completed": "\u2705", "cancelled": "\u274c"}
            lines = ["<b>Tasks:</b>"]
            for r in rows:
                icon = status_icons.get(r["status"], "\u2022")
                lines.append(f"{icon} [{r['priority'][:1].upper()}] {r['title']}")
            await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
            return

        if args[1] == "done":
            # Mark most recent in_progress task as completed
            row = conn.execute("SELECT id, title FROM tasks WHERE status = 'in_progress' ORDER BY updated_at DESC LIMIT 1").fetchone()
            if row:
                now = _time.time()
                conn.execute("UPDATE tasks SET status = 'completed', completed_at = ?, updated_at = ? WHERE id = ?", (now, now, row["id"]))
                conn.commit()
                conn.close()
                await message.answer(f"\u2705 Completed: {row['title']}")
            else:
                conn.close()
                await message.answer("No in-progress tasks to complete.")
            return

        if args[1] == "summary":
            rows = conn.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status").fetchall()
            conn.close()
            if not rows:
                await message.answer("No tasks.")
                return
            lines = ["<b>Task Summary:</b>"]
            for r in rows:
                lines.append(f"  {r['status']}: {r['cnt']}")
            await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
            return

        # Create a new task (everything after /task is the title)
        title = (message.text or "").split(None, 1)[1] if len(args) >= 2 else ""
        if not title:
            await message.answer("Usage:\n/task <title> \u2014 create task\n/task list [status]\n/task done\n/task summary")
            conn.close()
            return

        task_id = str(uuid.uuid4())
        now = _time.time()
        conn.execute(
            "INSERT INTO tasks (id, title, status, priority, created_at, updated_at, source) VALUES (?, ?, 'pending', 'normal', ?, ?, 'herald')",
            (task_id, title, now, now)
        )
        conn.commit()
        conn.close()
        await message.answer(f"\U0001f4cb Created: {title}")

    @dp.message(Command("scratchpad"))
    async def cmd_scratchpad(message: types.Message):
        """Read/write scratchpad notes. Usage: /scratchpad [name] [content]"""
        pad_dir = Path(config.homestead_data_dir).expanduser() / "scratchpad"
        pad_dir.mkdir(parents=True, exist_ok=True)

        args = (message.text or "").split(None, 2)  # /scratchpad, name, content

        if len(args) < 2:
            # List all notes
            files = sorted(pad_dir.glob("*.md"))
            if not files:
                await message.answer("Scratchpad is empty. Use /scratchpad <name> <content> to create a note.")
                return
            lines = ["<b>Scratchpad:</b>"]
            for f in files:
                size = f.stat().st_size
                lines.append(f"  \U0001f4dd {f.stem} ({size:,d} bytes)")
            lines.append("\nUse /scratchpad <name> to read a note")
            await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)
            return

        name = args[1]
        if not name.endswith(".md"):
            name_with_ext = name + ".md"
        else:
            name_with_ext = name
            name = name.rsplit(".", 1)[0]

        note_path = pad_dir / name_with_ext

        if len(args) < 3:
            # Read a note
            if not note_path.exists():
                await message.answer(f"Note '{name}' not found.")
                return
            content = note_path.read_text(encoding="utf-8")
            if len(content) > 3500:
                content = content[:3500] + "\n\n... (truncated)"
            await message.answer(f"<b>\U0001f4dd {name}</b>\n\n<pre>{html.escape(content)}</pre>", parse_mode=ParseMode.HTML)
            return

        # Write/append to a note
        content = args[2]
        if note_path.exists():
            existing = note_path.read_text(encoding="utf-8")
            note_path.write_text(existing + "\n\n" + content, encoding="utf-8")
            await message.answer(f"\U0001f4dd Appended to '{name}'")
        else:
            note_path.write_text(f"# {name}\n\n{content}\n", encoding="utf-8")
            await message.answer(f"\U0001f4dd Created '{name}'")

    # -- Proposal inline button handlers ------------------------------------

    @dp.callback_query(F.data.startswith("proposal_approve:"))
    async def handle_proposal_approve(callback: types.CallbackQuery):
        """Handle Approve button on proposal notification"""
        import httpx

        proposal_id = callback.data.split(":")[1]
        await callback.answer("Approving...")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://localhost:8700/api/proposals/{proposal_id}",
                    timeout=5.0
                )
                resp.raise_for_status()
                p = resp.json()

                # First approve the proposal
                resp = await client.patch(
                    f"http://localhost:8700/api/proposals/{proposal_id}",
                    json={"status": "approved", "review_notes": "Approved via Telegram"},
                    timeout=5.0
                )
                resp.raise_for_status()

                # Then apply it
                resp = await client.post(
                    f"http://localhost:8700/api/proposals/{proposal_id}/apply",
                    timeout=30.0
                )
                resp.raise_for_status()
                result = resp.json()

            msg = f"\u2705 <b>Proposal Applied!</b>\n\n"
            msg += f"<b>{p['title']}</b>\n"
            msg += f"Modified {len(p['file_paths'])} file(s)"

            if result.get('commit_sha'):
                msg += f"\n\nCommit: <code>{result['commit_sha'][:8]}</code>"

            await callback.message.edit_text(msg, parse_mode=ParseMode.HTML)

        except Exception as e:
            log.error("proposal approve failed for %s: %s", proposal_id, e)
            error_msg = f"\u274c <b>Error</b>\n\n{str(e)}"
            try:
                await callback.message.edit_text(error_msg, parse_mode=ParseMode.HTML)
            except Exception as edit_exc:
                log.warning("Failed to edit proposal error message: %s", edit_exc)
                await callback.message.answer(error_msg, parse_mode=ParseMode.HTML)

    @dp.callback_query(F.data.startswith("proposal_reject:"))
    async def handle_proposal_reject(callback: types.CallbackQuery):
        """Handle Reject button on proposal notification"""
        import httpx

        proposal_id = callback.data.split(":")[1]
        await callback.answer("Rejecting...")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"http://localhost:8700/api/proposals/{proposal_id}/reject",
                    json={"reason": "Rejected via Telegram"},
                    timeout=5.0
                )
                resp.raise_for_status()

            await callback.message.edit_text(
                f"\u274c <b>Proposal Rejected</b>\n\n{callback.message.html_text}",
                parse_mode=ParseMode.HTML
            )

        except Exception as e:
            log.error("proposal reject failed for %s: %s", proposal_id, e)
            error_msg = f"\u274c <b>Error</b>\n\n{str(e)}"
            try:
                await callback.message.edit_text(error_msg, parse_mode=ParseMode.HTML)
            except Exception as edit_exc:
                log.warning("Failed to edit proposal error message: %s", edit_exc)
                await callback.message.answer(error_msg, parse_mode=ParseMode.HTML)

    @dp.callback_query(F.data.startswith("proposal_info:"))
    async def handle_proposal_info(callback: types.CallbackQuery):
        """Handle More Info button on proposal notification"""
        import httpx
        from datetime import datetime

        proposal_id = callback.data.split(":")[1]
        await callback.answer("Fetching details...")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://localhost:8700/api/proposals/{proposal_id}",
                    timeout=5.0
                )
                resp.raise_for_status()
                p = resp.json()

            lines = [f"<b>{p['title']}</b>", "", p['description'], "", f"<b>Files:</b>"]
            for fpath in p['file_paths']:
                lines.append(f"  \u2022 <code>{fpath}</code>")

            diff = p.get('diff', '')
            if len(diff) > 1500:
                diff = diff[:1500] + "\n\n... (truncated)"
            if diff:
                lines.append("\n<b>Diff:</b>")
                lines.append(f"<pre>{diff}</pre>")

            await callback.message.answer("\n".join(lines), parse_mode=ParseMode.HTML)

        except Exception as e:
            await callback.message.answer(f"\u274c Error: {e}")

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        await message.answer(
            "/new \u2014 Start a fresh conversation\n"
            "/status \u2014 Show session info\n"
            "/session [name] [model] \u2014 Switch/create session\n"
            "/sessions \u2014 List all sessions\n"
            "/model [model] \u2014 Show/change model\n"
            "/task [title] \u2014 Create a task\n"
            "/task list [status] \u2014 List tasks\n"
            "/task done \u2014 Complete current task\n"
            "/task summary \u2014 Task counts\n"
            "/scratchpad \u2014 List notes\n"
            "/scratchpad <name> \u2014 Read a note\n"
            "/scratchpad <name> <text> \u2014 Write/append to a note\n"
            "/logs [hours] \u2014 Show log summary\n"
            "/cancel \u2014 Cancel current request\n"
            "/help \u2014 Show this message"
        )

    # -- Media messages --------------------------------------------------

    @dp.message(F.photo)
    async def handle_photo(message: types.Message):
        chat_id = message.chat.id
        try:
            photo = message.photo[-1]  # highest resolution
            file = await bot.get_file(photo.file_id)
            if not file.file_path:
                await message.answer("Could not download photo.")
                return

            scratchpad = Path(config.homestead_data_dir).expanduser() / "scratchpad"
            scratchpad.mkdir(parents=True, exist_ok=True)
            filename = f"img_{int(time.time())}_{photo.file_unique_id}.jpg"
            dest = scratchpad / filename
            await bot.download_file(file.file_path, str(dest))
            log.info("chat=%d photo saved: %s (%d bytes)", chat_id, dest.name, dest.stat().st_size)

            caption = message.caption or ""
            text = f"[User sent an image: {dest}]\n{caption}".strip()
        except Exception as exc:
            log.error("chat=%d photo download failed: %s", chat_id, exc)
            await message.answer("Failed to process photo.")
            return

        queued = QueuedMessage(
            chat_id=chat_id,
            user_id=message.from_user.id,
            text=text,
            timestamp=time.time(),
        )
        if not queue.enqueue(queued):
            await message.answer("Too many queued messages, try again later.")
            return

        if queue.is_active(chat_id):
            return

        asyncio.create_task(process_queue(bot, chat_id, config, sessions, queue))

    @dp.message(F.document)
    async def handle_document(message: types.Message):
        chat_id = message.chat.id
        doc = message.document
        try:
            file = await bot.get_file(doc.file_id)
            if not file.file_path:
                await message.answer("Could not download file.")
                return

            scratchpad = Path(config.homestead_data_dir).expanduser() / "scratchpad"
            scratchpad.mkdir(parents=True, exist_ok=True)
            safe_name = doc.file_name or doc.file_unique_id
            filename = f"doc_{int(time.time())}_{safe_name}"
            dest = scratchpad / filename
            await bot.download_file(file.file_path, str(dest))
            log.info("chat=%d document saved: %s (%d bytes)", chat_id, dest.name, dest.stat().st_size)

            caption = message.caption or ""
            text = f"[User sent a file: {dest} ({doc.file_name or 'unnamed'})]\n{caption}".strip()
        except Exception as exc:
            log.error("chat=%d document download failed: %s", chat_id, exc)
            await message.answer("Failed to process file.")
            return

        queued = QueuedMessage(
            chat_id=chat_id,
            user_id=message.from_user.id,
            text=text,
            timestamp=time.time(),
        )
        if not queue.enqueue(queued):
            await message.answer("Too many queued messages, try again later.")
            return

        if queue.is_active(chat_id):
            return

        asyncio.create_task(process_queue(bot, chat_id, config, sessions, queue))

    # -- Text messages ---------------------------------------------------

    @dp.message(F.text)
    async def handle_message(message: types.Message):
        chat_id = message.chat.id
        queued = QueuedMessage(
            chat_id=chat_id,
            user_id=message.from_user.id,
            text=message.text,
            timestamp=time.time(),
        )
        if not queue.enqueue(queued):
            await message.answer("Too many queued messages, try again later.")
            return

        if queue.is_active(chat_id):
            return

        asyncio.create_task(process_queue(bot, chat_id, config, sessions, queue))

    @dp.message(F.voice)
    async def handle_voice_message(message: types.Message):
        chat_id = message.chat.id
        await bot.send_chat_action(chat_id, ChatAction.TYPING)

        text = await handle_voice(bot, message)
        if text is None:
            await message.answer(
                "Voice messages require whisper for transcription.\n"
                "Install: pip install openai-whisper"
            )
            return

        # Feed transcribed text into the normal queue
        queued = QueuedMessage(
            chat_id=chat_id,
            user_id=message.from_user.id,
            text=text,
            timestamp=time.time(),
        )
        if not queue.enqueue(queued):
            await message.answer("Too many queued messages, try again later.")
            return

        # Show what was transcribed
        await message.answer(f"\U0001f3a4 <i>{text}</i>", parse_mode=ParseMode.HTML)

        if queue.is_active(chat_id):
            return

        asyncio.create_task(process_queue(bot, chat_id, config, sessions, queue))

    return bot, dp
