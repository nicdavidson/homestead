from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from common.db import get_connection
from common.models import LogEntry


_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  REAL    NOT NULL,
    level      TEXT    NOT NULL,
    source     TEXT    NOT NULL,
    message    TEXT    NOT NULL,
    data_json  TEXT,
    session_id TEXT,
    chat_id    INTEGER
)
"""

_CREATE_INDEX = """\
CREATE INDEX IF NOT EXISTS idx_logs_ts_level ON logs (timestamp, level)
"""


class Watchtower:
    """Structured logging sink backed by SQLite.

    Other packages add a :class:`WatchtowerHandler` to the stdlib logger.
    The AI can query the store directly via :meth:`query`, :meth:`errors_since`,
    and :meth:`summary`.
    """

    def __init__(self, db_path: str | Path = "~/.homestead/watchtower.db") -> None:
        self._db_path = Path(db_path).expanduser()
        self._conn = get_connection(self._db_path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.execute(_CREATE_INDEX)
        self._conn.commit()

    # -- write -----------------------------------------------------------------

    def log(
        self,
        level: str,
        source: str,
        message: str,
        data: dict | None = None,
        session_id: str | None = None,
        chat_id: int | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO logs (timestamp, level, source, message, data_json, session_id, chat_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                level,
                source,
                message,
                json.dumps(data) if data else None,
                session_id,
                chat_id,
            ),
        )
        self._conn.commit()

    # -- read ------------------------------------------------------------------

    def query(
        self,
        since: float | None = None,
        until: float | None = None,
        level: str | None = None,
        source: str | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        clauses: list[str] = []
        params: list = []

        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since)
        if until is not None:
            clauses.append("timestamp <= ?")
            params.append(until)
        if level is not None:
            clauses.append("level = ?")
            params.append(level)
        if source is not None:
            clauses.append("source LIKE ?")
            params.append(f"{source}%")
        if search is not None:
            clauses.append("message LIKE ?")
            params.append(f"%{search}%")

        where = " AND ".join(clauses) if clauses else "1=1"
        sql = f"SELECT * FROM logs WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def errors_since(self, hours: float = 24) -> list[LogEntry]:
        since = time.time() - hours * 3600
        return self.query(since=since, level="ERROR")

    def summary(self, hours: float = 24) -> dict[str, dict[str, int]]:
        since = time.time() - hours * 3600
        rows = self._conn.execute(
            "SELECT source, level, COUNT(*) as cnt FROM logs "
            "WHERE timestamp >= ? GROUP BY source, level ORDER BY source, level",
            (since,),
        ).fetchall()
        result: dict[str, dict[str, int]] = {}
        for row in rows:
            src = row["source"].split(".")[0]
            result.setdefault(src, {})[row["level"]] = row["cnt"]
        return result

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row) -> LogEntry:
        return LogEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            level=row["level"],
            source=row["source"],
            message=row["message"],
            data=json.loads(row["data_json"]) if row["data_json"] else None,
            session_id=row["session_id"],
            chat_id=row["chat_id"],
        )


class WatchtowerHandler(logging.Handler):
    """Python logging handler that writes to a :class:`Watchtower` instance."""

    def __init__(self, watchtower: Watchtower, source: str) -> None:
        super().__init__()
        self._wt = watchtower
        self._source = source

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._wt.log(
                level=record.levelname,
                source=f"{self._source}.{record.name}",
                message=record.getMessage(),
                data=getattr(record, "data", None),
            )
        except Exception:
            self.handleError(record)
