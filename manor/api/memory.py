"""Cronicle — Homestead memory system.

FTS5-backed document index across lore, scratchpad, and journal.
Provides unified search and context retrieval for the AI assistant.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .config import settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    id: str
    source: str
    path: str
    title: str
    snippet: str
    rank: float
    updated_at: float


@dataclass
class IndexStats:
    total_documents: int
    by_source: dict[str, int]
    last_reindex_at: float | None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS documents (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    path          TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL DEFAULT '',
    content       TEXT NOT NULL DEFAULT '',
    content_hash  TEXT NOT NULL DEFAULT '',
    doc_type      TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL,
    indexed_at    REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_updated ON documents(updated_at);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title,
    content,
    content=documents,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, title, content)
    VALUES (new.rowid, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, content)
    VALUES ('delete', old.rowid, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, content)
    VALUES ('delete', old.rowid, old.title, old.content);
    INSERT INTO documents_fts(rowid, title, content)
    VALUES (new.rowid, new.title, new.content);
END;

CREATE TABLE IF NOT EXISTS reindex_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   REAL NOT NULL,
    finished_at  REAL,
    docs_scanned INTEGER DEFAULT 0,
    docs_updated INTEGER DEFAULT 0,
    docs_added   INTEGER DEFAULT 0,
    docs_removed INTEGER DEFAULT 0
);
"""


# ---------------------------------------------------------------------------
# MemoryIndex
# ---------------------------------------------------------------------------


class MemoryIndex:
    """FTS5-backed document index for Cronicle."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else settings.memory_db
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(_SCHEMA)
        conn.commit()

    # -- Search ------------------------------------------------------------

    def search(
        self,
        query: str,
        source: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Full-text search across indexed documents."""
        conn = self._get_conn()

        # Sanitize query for FTS5: wrap in double quotes to treat as phrase
        safe_query = self._sanitize_query(query)
        if not safe_query:
            return []

        try:
            if source:
                rows = conn.execute(
                    """SELECT d.id, d.source, d.path, d.title,
                              snippet(documents_fts, 1, '**', '**', '...', 48) as snippet,
                              rank, d.updated_at
                       FROM documents_fts
                       JOIN documents d ON documents_fts.rowid = d.rowid
                       WHERE documents_fts MATCH ? AND d.source = ?
                       ORDER BY rank
                       LIMIT ?""",
                    (safe_query, source, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT d.id, d.source, d.path, d.title,
                              snippet(documents_fts, 1, '**', '**', '...', 48) as snippet,
                              rank, d.updated_at
                       FROM documents_fts
                       JOIN documents d ON documents_fts.rowid = d.rowid
                       WHERE documents_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (safe_query, limit),
                ).fetchall()
        except sqlite3.OperationalError:
            # FTS5 syntax error — try simpler fallback
            log.debug("FTS5 query failed, trying fallback: %s", safe_query)
            return []

        return [
            SearchResult(
                id=row["id"],
                source=row["source"],
                path=row["path"],
                title=row["title"],
                snippet=row["snippet"] or "",
                rank=row["rank"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Make a user query safe for FTS5."""
        # Strip FTS5 operators and wrap individual words
        words = []
        for word in query.split():
            # Remove FTS5 special chars
            cleaned = "".join(c for c in word if c.isalnum() or c in "-_'")
            if cleaned:
                words.append(cleaned)
        if not words:
            return ""
        # Join with OR for broader matching
        return " OR ".join(words)

    # -- Context building --------------------------------------------------

    def get_context_for_query(
        self,
        query: str,
        max_tokens: int = 2000,
        max_results: int = 5,
    ) -> str:
        """Build a context string for injection into the user prompt."""
        results = self.search(query, limit=max_results)
        if not results:
            return ""

        parts: list[str] = []
        budget = max_tokens
        for r in results:
            entry = f"- From {r.path}: {r.snippet}"
            # Rough token estimate: chars / 4
            tokens_est = len(entry) // 4
            if tokens_est > budget:
                break
            parts.append(entry)
            budget -= tokens_est

        if not parts:
            return ""

        return "[Relevant context from memory]:\n" + "\n".join(parts)

    # -- Upsert / Remove ---------------------------------------------------

    def upsert_document(
        self,
        source: str,
        path: str,
        content: str,
        title: str = "",
        doc_type: str = "",
        metadata: dict | None = None,
    ) -> bool:
        """Insert or update a document. Returns True if content changed."""
        conn = self._get_conn()
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check if exists and unchanged
        existing = conn.execute(
            "SELECT content_hash FROM documents WHERE path = ?", (path,)
        ).fetchone()

        if existing and existing["content_hash"] == content_hash:
            return False  # unchanged

        now = time.time()
        if not title:
            title = Path(path).stem

        if existing:
            conn.execute(
                "UPDATE documents SET source=?, title=?, content=?, content_hash=?, "
                "doc_type=?, metadata_json=?, updated_at=?, indexed_at=? WHERE path=?",
                (
                    source, title, content, content_hash,
                    doc_type or source, json_dumps(metadata or {}),
                    now, now, path,
                ),
            )
        else:
            conn.execute(
                "INSERT INTO documents "
                "(id, source, path, title, content, content_hash, doc_type, "
                "metadata_json, created_at, updated_at, indexed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()), source, path, title, content, content_hash,
                    doc_type or source, json_dumps(metadata or {}),
                    now, now, now,
                ),
            )
        conn.commit()
        return True

    def remove_document(self, path: str) -> bool:
        """Remove a document from the index. Returns True if it existed."""
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM documents WHERE path = ?", (path,))
        conn.commit()
        return cursor.rowcount > 0

    # -- Reindex -----------------------------------------------------------

    def reindex_directory(
        self,
        source: str,
        directory: Path,
        glob_pattern: str = "*.md",
    ) -> dict:
        """Reindex all matching files in a directory. Returns stats."""
        stats = {"scanned": 0, "added": 0, "updated": 0, "removed": 0}

        if not directory.is_dir():
            return stats

        conn = self._get_conn()

        # Get current indexed paths for this source
        indexed = {
            row["path"]
            for row in conn.execute(
                "SELECT path FROM documents WHERE source = ?", (source,)
            ).fetchall()
        }

        seen_paths: set[str] = set()

        for file_path in sorted(directory.glob(glob_pattern)):
            if not file_path.is_file():
                continue

            relative = f"{source}/{file_path.name}"
            seen_paths.add(relative)
            stats["scanned"] += 1

            try:
                content = file_path.read_text(encoding="utf-8").strip()
            except OSError:
                continue

            changed = self.upsert_document(source, relative, content)
            if relative not in indexed:
                stats["added"] += 1
            elif changed:
                stats["updated"] += 1

        # Remove docs that no longer exist on disk
        stale = indexed - seen_paths
        for path in stale:
            self.remove_document(path)
            stats["removed"] += 1

        return stats

    def reindex_all(self) -> dict:
        """Reindex all known directories (lore, scratchpad, journal)."""
        started = time.time()
        conn = self._get_conn()

        totals = {"scanned": 0, "added": 0, "updated": 0, "removed": 0}

        dirs = {
            "lore": settings.lore_path,
            "scratchpad": settings.scratchpad_dir,
            "journal": settings.journal_dir,
        }

        for source, directory in dirs.items():
            stats = self.reindex_directory(source, directory)
            for k in totals:
                totals[k] += stats[k]

        finished = time.time()
        conn.execute(
            "INSERT INTO reindex_log (started_at, finished_at, docs_scanned, "
            "docs_updated, docs_added, docs_removed) VALUES (?, ?, ?, ?, ?, ?)",
            (started, finished, totals["scanned"], totals["updated"],
             totals["added"], totals["removed"]),
        )
        conn.commit()

        log.info(
            "cronicle reindex: scanned=%d added=%d updated=%d removed=%d (%.1fs)",
            totals["scanned"], totals["added"], totals["updated"],
            totals["removed"], finished - started,
        )
        return totals

    # -- Stats -------------------------------------------------------------

    def get_stats(self) -> IndexStats:
        conn = self._get_conn()

        total = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]

        by_source: dict[str, int] = {}
        for row in conn.execute(
            "SELECT source, COUNT(*) as c FROM documents GROUP BY source"
        ).fetchall():
            by_source[row["source"]] = row["c"]

        last_log = conn.execute(
            "SELECT finished_at FROM reindex_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        last_reindex = last_log["finished_at"] if last_log else None

        return IndexStats(
            total_documents=total,
            by_source=by_source,
            last_reindex_at=last_reindex,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def json_dumps(obj: dict) -> str:
    import json
    return json.dumps(obj)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_index: MemoryIndex | None = None


def get_memory_index() -> MemoryIndex:
    """Get or create the singleton MemoryIndex."""
    global _index
    if _index is None:
        _index = MemoryIndex()
    return _index
