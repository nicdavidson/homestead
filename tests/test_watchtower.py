import logging
import time

from common.watchtower import Watchtower, WatchtowerHandler


def test_log_and_query(db_path):
    """Log entries and query them back."""
    wt = Watchtower(db_path)
    wt.log("INFO", "test.module", "first message")
    wt.log("INFO", "test.module", "second message")

    entries = wt.query()
    assert len(entries) == 2
    # Results are ordered by timestamp DESC, so newest first
    assert entries[0].message == "second message"
    assert entries[1].message == "first message"
    assert entries[0].level == "INFO"
    assert entries[0].source == "test.module"


def test_errors_since(db_path):
    """Log errors and info, verify errors_since returns only errors."""
    wt = Watchtower(db_path)
    wt.log("INFO", "app", "all good")
    wt.log("ERROR", "app", "something broke")
    wt.log("INFO", "app", "still fine")
    wt.log("ERROR", "app", "another failure")

    errors = wt.errors_since(hours=1)
    assert len(errors) == 2
    assert all(e.level == "ERROR" for e in errors)
    messages = {e.message for e in errors}
    assert "something broke" in messages
    assert "another failure" in messages


def test_summary(db_path):
    """Log from multiple sources, verify summary counts."""
    wt = Watchtower(db_path)
    wt.log("INFO", "herald", "msg1")
    wt.log("INFO", "herald", "msg2")
    wt.log("ERROR", "herald", "err1")
    wt.log("INFO", "nightshift", "msg1")
    wt.log("ERROR", "nightshift", "err1")

    summary = wt.summary(hours=1)
    assert summary["herald"]["INFO"] == 2
    assert summary["herald"]["ERROR"] == 1
    assert summary["nightshift"]["INFO"] == 1
    assert summary["nightshift"]["ERROR"] == 1


def test_query_filters(db_path):
    """Test since, until, level, source, search filters."""
    wt = Watchtower(db_path)

    now = time.time()

    # Insert with slight time gaps for ordering
    wt.log("INFO", "alpha", "hello world")
    wt.log("ERROR", "alpha", "bad thing")
    wt.log("INFO", "beta", "goodbye world")
    wt.log("WARNING", "beta.sub", "be careful")

    # Filter by level
    results = wt.query(level="ERROR")
    assert len(results) == 1
    assert results[0].message == "bad thing"

    # Filter by source (prefix match)
    results = wt.query(source="beta")
    assert len(results) == 2

    # Filter by search (substring match on message)
    results = wt.query(search="world")
    assert len(results) == 2

    # Filter by since (all entries are recent)
    results = wt.query(since=now - 10)
    assert len(results) == 4

    # Filter by until (far future gets everything)
    results = wt.query(until=time.time() + 100)
    assert len(results) == 4

    # Combined filters
    results = wt.query(level="INFO", source="alpha")
    assert len(results) == 1
    assert results[0].message == "hello world"


def test_watchtower_handler(db_path):
    """Create WatchtowerHandler, emit a LogRecord, verify it's stored."""
    wt = Watchtower(db_path)
    handler = WatchtowerHandler(wt, source="myapp")

    logger = logging.getLogger("test_watchtower_handler")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.info("handler test message")

    entries = wt.query()
    assert len(entries) == 1
    assert entries[0].message == "handler test message"
    assert entries[0].level == "INFO"
    # Source should be "{handler_source}.{logger_name}"
    assert entries[0].source == "myapp.test_watchtower_handler"

    # Clean up handler to avoid polluting other tests
    logger.removeHandler(handler)
