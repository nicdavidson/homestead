"""Homestead integration layer for hearth.

Connects hearth's AI entity personality layer to the shared homestead
infrastructure (watchtower logging, outbox messaging, skills, lore, tasks)
without modifying hearth's own codebase.
"""

import json
import logging
import sqlite3
import sys
import time
import uuid
from pathlib import Path

log = logging.getLogger("hearth.homestead")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_common_on_path() -> Path:
    """Add the common package to sys.path if not already present."""
    common_path = Path(__file__).resolve().parent.parent / "common"
    path_str = str(common_path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    return common_path


# ---------------------------------------------------------------------------
# 1. Watchtower integration
# ---------------------------------------------------------------------------

def setup_watchtower(homestead_data_dir: str = "~/.homestead"):
    """Add watchtower logging to hearth.

    Attaches a :class:`WatchtowerHandler` to the root logger so that every
    log record produced by hearth is also persisted in the shared watchtower
    database.  Returns the :class:`Watchtower` instance on success, or
    ``None`` if the common package is unavailable.
    """
    _ensure_common_on_path()

    try:
        from common.watchtower import Watchtower, WatchtowerHandler
    except ImportError:
        log.warning("common package not found, watchtower disabled for hearth")
        return None

    try:
        db_path = Path(homestead_data_dir).expanduser() / "watchtower.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        wt = Watchtower(str(db_path))
        handler = WatchtowerHandler(wt, source="hearth")
        logging.getLogger().addHandler(handler)
        log.debug("watchtower handler attached (db=%s)", db_path)
        return wt
    except Exception:
        log.exception("failed to initialise watchtower for hearth")
        return None


# ---------------------------------------------------------------------------
# 2. Outbox / Telegram integration
# ---------------------------------------------------------------------------

def send_to_telegram(
    chat_id: int,
    message: str,
    agent_name: str = "hearth",
    homestead_data_dir: str = "~/.homestead",
) -> None:
    """Send a message to Telegram via the shared outbox.

    The message is enqueued in the outbox database; the herald service is
    responsible for actually delivering it.
    """
    _ensure_common_on_path()

    from common.outbox import post_message

    db_path = Path(homestead_data_dir).expanduser() / "outbox.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        post_message(str(db_path), chat_id, agent_name, message)
        log.debug("outbox message enqueued for chat_id=%s via %s", chat_id, agent_name)
    except Exception:
        log.exception("failed to enqueue outbox message for chat_id=%s", chat_id)
        raise


# ---------------------------------------------------------------------------
# 3. Skills integration
# ---------------------------------------------------------------------------

def get_skill_manager(homestead_data_dir: str = "~/.homestead"):
    """Return a :class:`SkillManager` backed by the shared skills directory."""
    _ensure_common_on_path()

    from common.skills import SkillManager

    skills_dir = Path(homestead_data_dir).expanduser() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return SkillManager(skills_dir)


# ---------------------------------------------------------------------------
# 4. Lore integration
# ---------------------------------------------------------------------------

def read_lore(lore_dir: str | None = None) -> dict[str, str]:
    """Read all lore markdown files, returning ``{filename: content}``.

    If *lore_dir* is not provided, the default location relative to the
    homestead repository root is used.
    """
    if not lore_dir:
        lore_dir = str(Path(__file__).resolve().parent.parent.parent / "lore")

    lore_path = Path(lore_dir)
    result: dict[str, str] = {}

    if not lore_path.is_dir():
        log.warning("lore directory does not exist: %s", lore_path)
        return result

    for f in sorted(lore_path.glob("*.md")):
        try:
            result[f.name] = f.read_text(encoding="utf-8").strip()
        except OSError:
            log.warning("failed to read lore file: %s", f)

    log.debug("loaded %d lore files from %s", len(result), lore_path)
    return result


# ---------------------------------------------------------------------------
# 5. Task / steward integration
# ---------------------------------------------------------------------------

_TASKS_SCHEMA = """\
CREATE TABLE IF NOT EXISTS tasks (
    id              TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    priority        TEXT NOT NULL DEFAULT 'normal',
    assignee        TEXT DEFAULT 'auto',
    blockers_json   TEXT DEFAULT '[]',
    depends_on_json TEXT DEFAULT '[]',
    created_at      REAL NOT NULL,
    updated_at      REAL NOT NULL,
    completed_at    REAL,
    tags_json       TEXT DEFAULT '[]',
    notes_json      TEXT DEFAULT '[]',
    source          TEXT DEFAULT ''
)"""


def create_task(
    title: str,
    description: str = "",
    priority: str = "normal",
    tags: list[str] | None = None,
    homestead_data_dir: str = "~/.homestead",
) -> str:
    """Create a task in steward's task store.

    Returns the newly created task's UUID.
    """
    db_path = Path(homestead_data_dir).expanduser() / "steward" / "tasks.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute(_TASKS_SCHEMA)

        now = time.time()
        task_id = str(uuid.uuid4())

        conn.execute(
            "INSERT INTO tasks "
            "(id, title, description, status, priority, assignee, "
            " created_at, updated_at, tags_json, source) "
            "VALUES (?, ?, ?, 'pending', ?, 'auto', ?, ?, ?, 'hearth')",
            (task_id, title, description, priority, now, now, json.dumps(tags or [])),
        )
        conn.commit()
        log.debug("created task %s: %s", task_id, title)
        return task_id
    except Exception:
        log.exception("failed to create task: %s", title)
        raise
    finally:
        conn.close()
