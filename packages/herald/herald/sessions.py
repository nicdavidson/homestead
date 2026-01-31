from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from herald.config import Config


@dataclass
class SessionMeta:
    claude_session_id: str
    created_at: float
    last_active_at: float
    message_count: int = 0
    name: str = "default"
    model: str = "claude"
    is_active: bool = True
    # Keep these for backward compat but they're not used anymore
    chat_id: int = 0
    user_id: int = 0


# Global sessions - name is the primary key
_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS sessions (
    name              TEXT    PRIMARY KEY,
    claude_session_id TEXT    NOT NULL,
    model             TEXT    NOT NULL DEFAULT 'claude',
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        REAL    NOT NULL,
    last_active_at    REAL    NOT NULL,
    message_count     INTEGER NOT NULL DEFAULT 0
)
"""


class SessionManager:
    def __init__(self, config: Config) -> None:
        self._config = config
        db_dir = Path(config.data_dir)
        db_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = db_dir / "sessions.db"
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")

        # Migrate old schema to new schema if needed
        self._migrate_to_global_sessions()

        # Create table with new schema
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()
        self._migrate_json(config)

    # -- migration from old schema ---------------------------------------------

    def _migrate_to_global_sessions(self) -> None:
        """Migrate from per-chat sessions to global sessions."""
        try:
            # Check if old schema exists
            cursor = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            )
            if not cursor.fetchone():
                return  # No table yet, nothing to migrate

            # Check if it's the old schema (has chat_id as part of primary key)
            cursor = self._conn.execute("PRAGMA table_info(sessions)")
            columns = {row[1]: row for row in cursor.fetchall()}

            if "chat_id" not in columns or columns["name"][5] != 1:
                # Already migrated or new schema
                return

            # Backup old sessions
            self._conn.execute("ALTER TABLE sessions RENAME TO sessions_old")

            # Create new table
            self._conn.execute(_CREATE_TABLE)

            # Migrate data - take the most recently active session for each name
            self._conn.execute("""
                INSERT INTO sessions (name, claude_session_id, model, is_active,
                                     created_at, last_active_at, message_count)
                SELECT name, claude_session_id, model, is_active,
                       created_at, last_active_at, message_count
                FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY name ORDER BY last_active_at DESC) as rn
                    FROM sessions_old
                ) WHERE rn = 1
            """)

            # Ensure only one active session
            active_sessions = self._conn.execute(
                "SELECT name FROM sessions WHERE is_active = 1 ORDER BY last_active_at DESC"
            ).fetchall()

            if len(active_sessions) > 1:
                # Keep only the most recently active one
                most_recent = active_sessions[0][0]
                self._conn.execute(
                    "UPDATE sessions SET is_active = 0 WHERE name != ?", (most_recent,)
                )

            self._conn.commit()

            # Drop old table
            self._conn.execute("DROP TABLE sessions_old")
            self._conn.commit()

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Session migration failed: {e}", exc_info=True)
            # Rollback on error
            self._conn.rollback()

    # -- migration from old JSON format ----------------------------------------

    def _migrate_json(self, config: Config) -> None:
        """One-time migration from JSON files to SQLite."""
        json_dir = Path(config.data_dir) / "sessions"
        if not json_dir.exists():
            return
        import json

        for p in json_dir.glob("*.json"):
            if p.name == "archive":
                continue
            try:
                data = json.loads(p.read_text())
                existing = self._conn.execute(
                    "SELECT 1 FROM sessions WHERE name = 'default'",
                ).fetchone()
                if not existing:
                    self._conn.execute(
                        "INSERT INTO sessions (name, claude_session_id, "
                        "model, is_active, created_at, last_active_at, message_count) "
                        "VALUES ('default', ?, 'claude', 1, ?, ?, ?)",
                        (
                            data["claude_session_id"],
                            data["created_at"],
                            data["last_active_at"],
                            data.get("message_count", 0),
                        ),
                    )
                    self._conn.commit()
                p.unlink()
            except Exception:
                pass

    # -- read ------------------------------------------------------------------

    def get_active(self, chat_id: int | None = None) -> SessionMeta | None:
        """Get the globally active session (chat_id ignored for backward compat)."""
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE is_active = 1",
        ).fetchone()
        return self._row_to_meta(row) if row else None

    def get(self, chat_id: int | None = None) -> SessionMeta | None:
        """Alias for get_active (backward compat)."""
        return self.get_active(chat_id)

    def get_by_name(self, chat_id: int | None, name: str) -> SessionMeta | None:
        """Get session by name (chat_id ignored for backward compat)."""
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE name = ?",
            (name,),
        ).fetchone()
        return self._row_to_meta(row) if row else None

    def list_sessions(self, chat_id: int | None = None) -> list[SessionMeta]:
        """List all global sessions (chat_id ignored for backward compat)."""
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY last_active_at DESC",
        ).fetchall()
        return [self._row_to_meta(r) for r in rows]

    # -- write -----------------------------------------------------------------

    def create(self, chat_id: int, user_id: int, name: str = "default", model: str = "claude") -> SessionMeta:
        """Create or replace a global session (chat_id/user_id kept for backward compat)."""
        now = time.time()
        session_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions "
            "(name, claude_session_id, model, is_active, created_at, last_active_at, message_count) "
            "VALUES (?, ?, ?, 1, ?, ?, 0)",
            (name, session_id, model, now, now),
        )
        # Deactivate all other sessions
        self._conn.execute(
            "UPDATE sessions SET is_active = 0 WHERE name != ?",
            (name,),
        )
        self._conn.commit()
        return SessionMeta(
            claude_session_id=session_id,
            created_at=now,
            last_active_at=now,
            name=name,
            model=model,
            is_active=True,
            chat_id=chat_id,
            user_id=user_id,
        )

    def switch(self, chat_id: int | None, name: str) -> SessionMeta | None:
        """Switch to an existing named session globally (chat_id ignored)."""
        session = self.get_by_name(None, name)
        if session is None:
            return None
        self._conn.execute(
            "UPDATE sessions SET is_active = 0"
        )
        self._conn.execute(
            "UPDATE sessions SET is_active = 1 WHERE name = ?",
            (name,),
        )
        self._conn.commit()
        session.is_active = True
        return session

    def touch(self, session: SessionMeta) -> None:
        """Update session activity."""
        session.last_active_at = time.time()
        session.message_count += 1
        self._conn.execute(
            "UPDATE sessions SET last_active_at = ?, message_count = ? "
            "WHERE name = ?",
            (session.last_active_at, session.message_count, session.name),
        )
        self._conn.commit()

    def rotate(self, chat_id: int, user_id: int, name: str = "default", model: str = "claude") -> SessionMeta:
        """Archive old session and create a fresh one."""
        return self.create(chat_id, user_id, name, model)

    def set_model(self, chat_id: int | None, name: str, model: str) -> None:
        """Change the model for an existing session (chat_id ignored)."""
        self._conn.execute(
            "UPDATE sessions SET model = ? WHERE name = ?",
            (model, name),
        )
        self._conn.commit()

    def update_session_id(self, session: SessionMeta, new_id: str) -> None:
        """Update the Claude CLI session ID (after first response)."""
        session.claude_session_id = new_id
        self._conn.execute(
            "UPDATE sessions SET claude_session_id = ? WHERE name = ?",
            (new_id, session.name),
        )
        self._conn.commit()

    def is_stale(self, session: SessionMeta) -> bool:
        hours_inactive = (time.time() - session.last_active_at) / 3600
        return hours_inactive > self._config.session_inactivity_hours

    # -- internal --------------------------------------------------------------

    def _save(self, session: SessionMeta) -> None:
        """Update all fields (backward compat helper)."""
        self._conn.execute(
            "UPDATE sessions SET claude_session_id = ?, last_active_at = ?, message_count = ? "
            "WHERE name = ?",
            (
                session.claude_session_id,
                session.last_active_at,
                session.message_count,
                session.name,
            ),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_meta(row) -> SessionMeta:
        return SessionMeta(
            claude_session_id=row["claude_session_id"],
            created_at=row["created_at"],
            last_active_at=row["last_active_at"],
            message_count=row["message_count"],
            name=row["name"],
            model=row["model"],
            is_active=bool(row["is_active"]),
            chat_id=0,  # Not stored anymore
            user_id=0,  # Not stored anymore
        )
