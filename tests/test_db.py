import sqlite3
from pathlib import Path

from common.db import get_connection


def test_get_connection(tmp_dir):
    """Creates db file, returns connection with WAL mode."""
    db_path = tmp_dir / "test_conn.db"
    conn = get_connection(db_path)

    assert isinstance(conn, sqlite3.Connection)
    assert db_path.exists()

    # Verify row_factory is set (returns Row objects, not tuples)
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (42)")
    row = conn.execute("SELECT x FROM t").fetchone()
    assert row["x"] == 42

    conn.close()


def test_wal_mode(tmp_dir):
    """Verify PRAGMA journal_mode returns wal."""
    db_path = tmp_dir / "test_wal.db"
    conn = get_connection(db_path)

    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"

    conn.close()


def test_creates_parent_dirs(tmp_dir):
    """Path with nonexistent parent gets created."""
    db_path = tmp_dir / "deep" / "nested" / "dir" / "test.db"
    assert not db_path.parent.exists()

    conn = get_connection(db_path)
    assert db_path.parent.exists()
    assert db_path.exists()

    conn.close()
