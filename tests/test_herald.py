"""Herald test suite — ensures bot stability and catches corruption.

Herald keeps breaking when proposals modify its source files. These tests
verify every module imports, key classes have the right shape, and the
core logic (sessions, queue, auth, prompt) works correctly.
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add herald package to sys.path
_herald_pkg = Path(__file__).parent.parent / "packages" / "herald"
if str(_herald_pkg) not in sys.path:
    sys.path.insert(0, str(_herald_pkg))


# ---------------------------------------------------------------------------
# Import smoke tests — these catch file corruption/truncation
# ---------------------------------------------------------------------------

class TestImports:
    """Every Herald module must import without error."""

    def test_import_config(self):
        from herald.config import Config, load_config
        assert callable(load_config)
        assert "telegram_bot_token" in Config.__dataclass_fields__
        assert "allowed_user_ids" in Config.__dataclass_fields__

    def test_import_bot(self):
        from herald.bot import create_bot, poll_outbox
        assert callable(create_bot)
        assert callable(poll_outbox)

    def test_import_claude(self):
        from herald.claude import (
            spawn_claude, kill_process, kill_claude,
            ClaudeResult, ClaudeError, RateLimitError, SessionNotFoundError,
            register_process, unregister_process,
        )
        assert callable(spawn_claude)
        assert callable(kill_process)
        assert callable(kill_claude)

    def test_import_sessions(self):
        from herald.sessions import SessionManager, SessionMeta
        assert callable(SessionManager)

    def test_import_queue(self):
        from herald.queue import MessageQueue, QueuedMessage
        assert callable(MessageQueue)

    def test_import_providers(self):
        from herald.providers import dispatch_message, refresh_prompt
        assert callable(dispatch_message)
        assert callable(refresh_prompt)

    def test_import_prompt(self):
        from herald.prompt import assemble_system_prompt
        assert callable(assemble_system_prompt)

    def test_import_auth(self):
        from herald.auth import is_authorized
        assert callable(is_authorized)

    def test_import_voice(self):
        from herald.voice import handle_voice
        assert callable(handle_voice)

    def test_import_middleware(self):
        from herald.middleware import RateLimitMiddleware, LoggingMiddleware
        assert RateLimitMiddleware is not None
        assert LoggingMiddleware is not None


# ---------------------------------------------------------------------------
# File integrity checks — catch truncation and corruption
# ---------------------------------------------------------------------------

class TestFileIntegrity:
    """Verify key files haven't been truncated or corrupted."""

    def test_bot_minimum_size(self):
        """bot.py should be at least 500 lines."""
        bot_file = _herald_pkg / "herald" / "bot.py"
        content = bot_file.read_text()
        line_count = len(content.splitlines())
        assert line_count >= 500, (
            f"bot.py is only {line_count} lines — expected 500+. "
            f"File may be corrupted or truncated."
        )

    def test_bot_has_command_handlers(self):
        """bot.py must define command handlers."""
        import herald.bot as bot_mod
        import inspect
        source = inspect.getsource(bot_mod)
        assert "Command(" in source, "bot.py must have Command handlers"
        assert "create_bot" in source
        assert "process_queue" in source

    def test_bot_create_bot_signature(self):
        """create_bot must accept config, sessions, queue."""
        from herald.bot import create_bot
        import inspect
        sig = inspect.signature(create_bot)
        param_names = list(sig.parameters.keys())
        assert "config" in param_names
        assert "sessions" in param_names
        assert "queue" in param_names

    def test_claude_has_spawn(self):
        """claude.py must define spawn_claude with the right signature."""
        from herald.claude import spawn_claude
        import inspect
        sig = inspect.signature(spawn_claude)
        param_names = list(sig.parameters.keys())
        assert "prompt" in param_names
        assert "session_id" in param_names
        assert "config" in param_names

    def test_all_modules_exist(self):
        """All expected .py files must be present in herald/."""
        expected = [
            "auth.py", "bot.py", "claude.py", "config.py",
            "main.py", "middleware.py", "prompt.py",
            "providers.py", "queue.py", "sessions.py", "voice.py",
        ]
        herald_dir = _herald_pkg / "herald"
        for name in expected:
            assert (herald_dir / name).is_file(), f"Missing: herald/{name}"


# ---------------------------------------------------------------------------
# SessionManager tests
# ---------------------------------------------------------------------------

class TestSessionManager:
    """Test session CRUD operations."""

    @pytest.fixture
    def config(self, tmp_path):
        from herald.config import Config
        return Config(
            telegram_bot_token="test-token",
            allowed_user_ids=[123],
            data_dir=str(tmp_path),
            session_inactivity_hours=4.0,
        )

    @pytest.fixture
    def sessions(self, config):
        from herald.sessions import SessionManager
        return SessionManager(config)

    def test_create_session(self, sessions):
        s = sessions.create(chat_id=100, user_id=123, name="test")
        assert s.name == "test"
        assert s.is_active is True
        assert s.message_count == 0

    def test_get_active(self, sessions):
        sessions.create(chat_id=100, user_id=123, name="active")
        active = sessions.get_active(100)
        assert active is not None
        assert active.name == "active"

    def test_get_active_returns_none_when_empty(self, sessions):
        assert sessions.get_active(100) is None

    def test_create_deactivates_others(self, sessions):
        sessions.create(chat_id=100, user_id=123, name="first")
        sessions.create(chat_id=100, user_id=123, name="second")
        active = sessions.get_active(100)
        assert active.name == "second"

        first = sessions.get_by_name(100, "first")
        assert first is not None
        assert first.is_active is False

    def test_switch_session(self, sessions):
        sessions.create(chat_id=100, user_id=123, name="a")
        sessions.create(chat_id=100, user_id=123, name="b")

        switched = sessions.switch(100, "a")
        assert switched is not None
        assert switched.name == "a"
        assert switched.is_active is True

        active = sessions.get_active(100)
        assert active.name == "a"

    def test_switch_nonexistent_returns_none(self, sessions):
        result = sessions.switch(100, "nope")
        assert result is None

    def test_touch_updates_activity(self, sessions):
        s = sessions.create(chat_id=100, user_id=123, name="test")
        original_time = s.last_active_at
        original_count = s.message_count

        time.sleep(0.01)
        sessions.touch(s)

        assert s.last_active_at > original_time
        assert s.message_count == original_count + 1

    def test_list_sessions(self, sessions):
        sessions.create(chat_id=100, user_id=123, name="a")
        sessions.create(chat_id=100, user_id=123, name="b")
        all_sessions = sessions.list_sessions(100)
        assert len(all_sessions) == 2
        names = {s.name for s in all_sessions}
        assert names == {"a", "b"}

    def test_set_model(self, sessions):
        sessions.create(chat_id=100, user_id=123, name="test", model="claude")
        sessions.set_model(100, "test", "grok")
        s = sessions.get_by_name(100, "test")
        assert s.model == "grok"

    def test_update_session_id(self, sessions):
        s = sessions.create(chat_id=100, user_id=123, name="test")
        sessions.update_session_id(s, "new-session-id")
        assert s.claude_session_id == "new-session-id"

        reloaded = sessions.get_by_name(100, "test")
        assert reloaded.claude_session_id == "new-session-id"

    def test_is_stale(self, sessions):
        s = sessions.create(chat_id=100, user_id=123, name="test")
        assert sessions.is_stale(s) is False

        s.last_active_at = time.time() - 5 * 3600
        assert sessions.is_stale(s) is True


# ---------------------------------------------------------------------------
# MessageQueue tests
# ---------------------------------------------------------------------------

class TestMessageQueue:
    """Test message queue behavior."""

    @pytest.fixture
    def queue(self):
        from herald.queue import MessageQueue
        return MessageQueue(max_size=3)

    @pytest.fixture
    def msg(self):
        from herald.queue import QueuedMessage
        return QueuedMessage(chat_id=100, user_id=123, text="hello", timestamp=time.time())

    def test_enqueue_dequeue(self, queue, msg):
        assert queue.enqueue(msg) is True
        result = queue.dequeue(100)
        assert result is not None
        assert result.text == "hello"

    def test_dequeue_empty(self, queue):
        assert queue.dequeue(100) is None

    def test_max_size(self, queue):
        from herald.queue import QueuedMessage
        for i in range(3):
            assert queue.enqueue(
                QueuedMessage(chat_id=100, user_id=123, text=f"msg{i}", timestamp=time.time())
            ) is True
        assert queue.enqueue(
            QueuedMessage(chat_id=100, user_id=123, text="overflow", timestamp=time.time())
        ) is False

    def test_fifo_order(self, queue):
        from herald.queue import QueuedMessage
        for i in range(3):
            queue.enqueue(
                QueuedMessage(chat_id=100, user_id=123, text=f"msg{i}", timestamp=time.time())
            )
        assert queue.dequeue(100).text == "msg0"
        assert queue.dequeue(100).text == "msg1"
        assert queue.dequeue(100).text == "msg2"

    def test_active_idle(self, queue):
        assert queue.is_active(100) is False
        queue.mark_active(100)
        assert queue.is_active(100) is True
        queue.mark_idle(100)
        assert queue.is_active(100) is False

    def test_clear(self, queue, msg):
        queue.enqueue(msg)
        queue.clear(100)
        assert queue.dequeue(100) is None

    def test_separate_chat_queues(self, queue):
        from herald.queue import QueuedMessage
        queue.enqueue(QueuedMessage(chat_id=100, user_id=1, text="a", timestamp=time.time()))
        queue.enqueue(QueuedMessage(chat_id=200, user_id=2, text="b", timestamp=time.time()))
        assert queue.dequeue(100).text == "a"
        assert queue.dequeue(200).text == "b"
        assert queue.dequeue(100) is None


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class TestAuth:
    """Test authorization logic."""

    @pytest.fixture
    def config(self):
        from herald.config import Config
        return Config(
            telegram_bot_token="test",
            allowed_user_ids=[111, 222],
        )

    def test_authorized_user(self, config):
        from herald.auth import is_authorized
        assert is_authorized(111, config) is True
        assert is_authorized(222, config) is True

    def test_unauthorized_user(self, config):
        from herald.auth import is_authorized
        assert is_authorized(999, config) is False

    def test_empty_allowlist(self):
        from herald.auth import is_authorized
        from herald.config import Config
        config = Config(telegram_bot_token="test", allowed_user_ids=[])
        assert is_authorized(111, config) is False


# ---------------------------------------------------------------------------
# Prompt assembly tests
# ---------------------------------------------------------------------------

class TestPromptAssembly:
    """Test system prompt construction."""

    @pytest.fixture
    def lore_dir(self, tmp_path):
        lore = tmp_path / "lore"
        lore.mkdir()
        return lore

    @pytest.fixture
    def config(self, tmp_path, lore_dir):
        from herald.config import Config
        return Config(
            telegram_bot_token="test",
            allowed_user_ids=[123],
            lore_dir=str(lore_dir),
            homestead_data_dir=str(tmp_path / "homestead"),
            agent_name="TestBot",
            system_prompt="Fallback prompt",
        )

    def test_fallback_when_no_lore(self, tmp_path):
        """With no lore_dir and no homestead dir, prompt is minimal."""
        from herald.prompt import assemble_system_prompt
        from herald.config import Config
        config = Config(
            telegram_bot_token="test",
            allowed_user_ids=[],
            lore_dir="",
            homestead_data_dir=str(tmp_path / "nope"),
            system_prompt="Fallback prompt",
        )
        result = assemble_system_prompt(config)
        # No soul/identity/claude files → only user.md reminder section
        assert isinstance(result, str)
        assert len(result) > 0

    def test_loads_soul(self, config, lore_dir):
        from herald.prompt import assemble_system_prompt
        (lore_dir / "soul.md").write_text("# Soul\nI am a test bot.")
        result = assemble_system_prompt(config)
        assert "I am a test bot" in result

    def test_loads_identity(self, config, lore_dir):
        from herald.prompt import assemble_system_prompt
        (lore_dir / "identity.md").write_text("# Identity\nMy name is TestBot.")
        result = assemble_system_prompt(config)
        assert "My name is TestBot" in result

    def test_loads_user(self, config, lore_dir):
        from herald.prompt import assemble_system_prompt
        (lore_dir / "user.md").write_text("# User\nNic is a developer.")
        result = assemble_system_prompt(config)
        assert "Nic is a developer" in result

    def test_missing_user_adds_reminder(self, config, lore_dir):
        from herald.prompt import assemble_system_prompt
        (lore_dir / "soul.md").write_text("# Soul")
        result = assemble_system_prompt(config)
        assert "No user.md found" in result

    def test_loads_extra_lore_files(self, config, lore_dir):
        from herald.prompt import assemble_system_prompt
        (lore_dir / "soul.md").write_text("# Soul")
        (lore_dir / "projects.md").write_text("# Projects\nHomestead is great.")
        result = assemble_system_prompt(config)
        assert "Homestead is great" in result

    def test_includes_mcp_section_when_configured(self, lore_dir, tmp_path):
        from herald.prompt import assemble_system_prompt
        from herald.config import Config
        config = Config(
            telegram_bot_token="test",
            allowed_user_ids=[],
            lore_dir=str(lore_dir),
            homestead_data_dir=str(tmp_path / "homestead"),
            mcp_config_path="/fake/mcp-config.json",
        )
        (lore_dir / "soul.md").write_text("# Soul")
        result = assemble_system_prompt(config)
        assert "MCP Tools" in result
        assert "propose_code_change" in result

    def test_skills_section(self, config, lore_dir, tmp_path):
        from herald.prompt import assemble_system_prompt
        skills_dir = tmp_path / "homestead" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "commit.md").write_text(
            "---\nname: commit\ndescription: Create git commits\n---\nBody here"
        )
        (lore_dir / "soul.md").write_text("# Soul")
        result = assemble_system_prompt(config)
        assert "commit" in result
        assert "Create git commits" in result

    def test_scratchpad_section(self, config, lore_dir, tmp_path):
        from herald.prompt import assemble_system_prompt
        pad_dir = tmp_path / "homestead" / "scratchpad"
        pad_dir.mkdir(parents=True)
        (pad_dir / "notes.md").write_text("Some notes")
        (lore_dir / "soul.md").write_text("# Soul")
        result = assemble_system_prompt(config)
        assert "notes" in result


# ---------------------------------------------------------------------------
# ClaudeResult and exception tests
# ---------------------------------------------------------------------------

class TestClaudeResult:
    """Verify ClaudeResult has all expected fields."""

    def test_defaults(self):
        from herald.claude import ClaudeResult
        r = ClaudeResult(text="hello", session_id="abc")
        assert r.text == "hello"
        assert r.session_id == "abc"
        assert r.model == ""
        assert r.input_tokens == 0
        assert r.output_tokens == 0
        assert r.cost_usd is None
        assert r.num_turns == 0

    def test_with_usage(self):
        from herald.claude import ClaudeResult
        r = ClaudeResult(
            text="hello", session_id="abc",
            input_tokens=1000, output_tokens=500,
            cost_usd=0.05, num_turns=3,
        )
        assert r.input_tokens == 1000
        assert r.cost_usd == 0.05
        assert r.num_turns == 3


class TestExceptions:
    """Verify exception classes exist and inherit correctly."""

    def test_claude_error(self):
        from herald.claude import ClaudeError
        assert issubclass(ClaudeError, Exception)

    def test_rate_limit_error(self):
        from herald.claude import RateLimitError
        assert issubclass(RateLimitError, Exception)

    def test_session_not_found_error(self):
        from herald.claude import SessionNotFoundError
        assert issubclass(SessionNotFoundError, Exception)
