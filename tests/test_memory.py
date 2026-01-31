"""Unit tests for Cronicle memory system (manor/api/memory.py)."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "manor"))

# Patch settings before importing memory module
_tmp_dir = tempfile.mkdtemp()
os.environ.setdefault("HOMESTEAD_DATA_DIR", _tmp_dir)

from api.memory import MemoryIndex, SearchResult  # noqa: E402


@pytest.fixture
def idx(tmp_path):
    """Create a fresh MemoryIndex backed by a temp DB."""
    db_path = tmp_path / "test_memory.db"
    return MemoryIndex(db_path=db_path)


class TestSchema:
    def test_schema_creation(self, idx):
        conn = idx._get_conn()
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            ).fetchall()
        }
        assert "documents" in tables
        assert "documents_fts" in tables
        assert "reindex_log" in tables


class TestUpsert:
    def test_insert_new_document(self, idx):
        changed = idx.upsert_document("lore", "lore/test.md", "Hello world", title="Test")
        assert changed is True

    def test_skip_unchanged_document(self, idx):
        idx.upsert_document("lore", "lore/test.md", "Hello world")
        changed = idx.upsert_document("lore", "lore/test.md", "Hello world")
        assert changed is False

    def test_update_changed_document(self, idx):
        idx.upsert_document("lore", "lore/test.md", "Hello world")
        changed = idx.upsert_document("lore", "lore/test.md", "Updated content")
        assert changed is True

    def test_auto_title_from_path(self, idx):
        idx.upsert_document("lore", "lore/my-document.md", "content")
        conn = idx._get_conn()
        row = conn.execute("SELECT title FROM documents WHERE path = ?", ("lore/my-document.md",)).fetchone()
        assert row["title"] == "my-document"


class TestRemove:
    def test_remove_existing_document(self, idx):
        idx.upsert_document("lore", "lore/test.md", "content")
        removed = idx.remove_document("lore/test.md")
        assert removed is True

    def test_remove_nonexistent_document(self, idx):
        removed = idx.remove_document("lore/nope.md")
        assert removed is False


class TestSearch:
    def test_basic_search(self, idx):
        idx.upsert_document("lore", "lore/soul.md", "The soul of the homestead system is collaboration")
        idx.upsert_document("lore", "lore/identity.md", "I am an AI assistant named Claude")
        results = idx.search("soul collaboration")
        assert len(results) >= 1
        assert results[0].path == "lore/soul.md"

    def test_search_with_source_filter(self, idx):
        idx.upsert_document("lore", "lore/doc.md", "Important document content")
        idx.upsert_document("scratchpad", "scratchpad/notes.md", "Important scratchpad content")
        results = idx.search("important", source="scratchpad")
        assert all(r.source == "scratchpad" for r in results)

    def test_search_empty_query(self, idx):
        idx.upsert_document("lore", "lore/test.md", "some content")
        results = idx.search("")
        assert results == []

    def test_search_special_characters(self, idx):
        idx.upsert_document("lore", "lore/test.md", "Hello world")
        # Should not crash on FTS5 special chars
        results = idx.search('hello OR "world AND NOT test')
        assert isinstance(results, list)

    def test_search_returns_search_result(self, idx):
        idx.upsert_document("lore", "lore/test.md", "unique content here")
        results = idx.search("unique")
        assert len(results) >= 1
        r = results[0]
        assert isinstance(r, SearchResult)
        assert r.source == "lore"
        assert r.path == "lore/test.md"


class TestContext:
    def test_context_for_query(self, idx):
        idx.upsert_document("lore", "lore/soul.md", "The soul of the system is important")
        ctx = idx.get_context_for_query("soul system")
        assert "memory" in ctx.lower() or "context" in ctx.lower()
        assert "soul" in ctx.lower()

    def test_empty_context_when_no_results(self, idx):
        ctx = idx.get_context_for_query("nonexistent term xyzzy")
        assert ctx == ""

    def test_context_respects_token_budget(self, idx):
        # Insert many docs
        for i in range(20):
            idx.upsert_document("lore", f"lore/doc{i}.md", f"common word document number {i} " * 100)
        ctx = idx.get_context_for_query("common word", max_tokens=100)
        # Should be trimmed, not all 20 docs
        assert len(ctx) < 2000


class TestReindex:
    def test_reindex_directory(self, idx, tmp_path):
        doc_dir = tmp_path / "lore"
        doc_dir.mkdir()
        (doc_dir / "file1.md").write_text("First file content")
        (doc_dir / "file2.md").write_text("Second file content")
        (doc_dir / "readme.txt").write_text("Not indexed")

        stats = idx.reindex_directory("lore", doc_dir)
        assert stats["scanned"] == 2
        assert stats["added"] == 2
        assert stats["removed"] == 0

    def test_reindex_removes_stale(self, idx, tmp_path):
        doc_dir = tmp_path / "lore"
        doc_dir.mkdir()
        (doc_dir / "file1.md").write_text("content")
        idx.reindex_directory("lore", doc_dir)

        # Remove the file and reindex
        (doc_dir / "file1.md").unlink()
        stats = idx.reindex_directory("lore", doc_dir)
        assert stats["removed"] == 1

    def test_reindex_nonexistent_dir(self, idx, tmp_path):
        stats = idx.reindex_directory("lore", tmp_path / "nope")
        assert stats["scanned"] == 0

    def test_reindex_skips_unchanged(self, idx, tmp_path):
        doc_dir = tmp_path / "lore"
        doc_dir.mkdir()
        (doc_dir / "file1.md").write_text("stable content")
        idx.reindex_directory("lore", doc_dir)

        stats = idx.reindex_directory("lore", doc_dir)
        assert stats["updated"] == 0
        assert stats["added"] == 0


class TestStats:
    def test_stats_empty(self, idx):
        stats = idx.get_stats()
        assert stats.total_documents == 0
        assert stats.by_source == {}
        assert stats.last_reindex_at is None

    def test_stats_with_documents(self, idx):
        idx.upsert_document("lore", "lore/a.md", "content a")
        idx.upsert_document("lore", "lore/b.md", "content b")
        idx.upsert_document("journal", "journal/2025-01-01.md", "journal entry")
        stats = idx.get_stats()
        assert stats.total_documents == 3
        assert stats.by_source["lore"] == 2
        assert stats.by_source["journal"] == 1


class TestSanitizeQuery:
    def test_strips_special_chars(self):
        assert MemoryIndex._sanitize_query("hello* world!") == "hello OR world"

    def test_empty_query(self):
        assert MemoryIndex._sanitize_query("") == ""

    def test_preserves_hyphens(self):
        assert MemoryIndex._sanitize_query("self-reflection") == "self-reflection"
