"""Tests for the proposals system — especially file resolution safety checks.

The bot.py corruption was caused by _resolve_file silently replacing
a 752-line file with a 122-line snippet. These tests ensure:
  1. Snippet matching works correctly when snippet IS found
  2. Snippet-not-found raises an error (no silent full-file replace)
  3. Size guard rejects drastically smaller replacements
  4. Multi-file proposals create per-file rows
  5. Legacy single-file proposals still work
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add manor to sys.path so we can import proposals internals
_manor_root = Path(__file__).parent.parent / "manor"
if str(_manor_root) not in sys.path:
    sys.path.insert(0, str(_manor_root))

# Mock settings before importing proposals (it reads settings at import time)
_mock_settings = MagicMock()
_mock_settings.proposals_db = Path("/tmp/fake_proposals.db")
with patch.dict("sys.modules", {}):
    pass

# Pre-patch settings so the module-level import doesn't fail
import api.config
_original_settings = api.config.settings

import api.routers.proposals as proposals_mod
from api.routers.proposals import _resolve_file, CreateProposalBody, ProposalFile
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo_dir(tmp_path):
    """Temp directory that acts as the repo root for proposals."""
    return tmp_path


@pytest.fixture
def resolve(repo_dir):
    """Return _resolve_file with REPO_ROOT pointed at tmp dir."""
    original_root = proposals_mod.REPO_ROOT
    proposals_mod.REPO_ROOT = str(repo_dir)
    yield _resolve_file
    proposals_mod.REPO_ROOT = original_root


@pytest.fixture
def proposals_db(tmp_path):
    """Provide a temp proposals DB path."""
    db_path = tmp_path / "data" / "proposals.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


@pytest.fixture
def setup_api(repo_dir, proposals_db):
    """Patch settings and REPO_ROOT for proposal creation tests."""
    mock_settings = MagicMock()
    mock_settings.proposals_db = proposals_db

    original_root = proposals_mod.REPO_ROOT
    original_settings = proposals_mod.settings

    proposals_mod.REPO_ROOT = str(repo_dir)
    proposals_mod.settings = mock_settings

    yield repo_dir

    proposals_mod.REPO_ROOT = original_root
    proposals_mod.settings = original_settings


# ---------------------------------------------------------------------------
# _resolve_file: snippet matching
# ---------------------------------------------------------------------------

class TestResolveFileSnippet:
    """Tests for snippet detection and replacement in _resolve_file."""

    def test_exact_match_full_file(self, repo_dir, resolve):
        """When original_content matches the full file, replace entirely."""
        original = "line1\nline2\nline3\n"
        new = "line1\nLINE2_CHANGED\nline3\n"
        (repo_dir / "test.py").write_text(original)

        actual_orig, full_new, diff = resolve("test.py", original, new)
        assert actual_orig == original
        assert full_new == new
        assert "LINE2_CHANGED" in diff

    def test_snippet_found_replaces_section(self, repo_dir, resolve):
        """When original_content is a snippet, splice new_content into the file."""
        full_file = "# header\ndef foo():\n    pass\n# footer\n"
        snippet_orig = "def foo():\n    pass"
        snippet_new = "def foo():\n    return 42"
        (repo_dir / "test.py").write_text(full_file)

        actual_orig, full_new, diff = resolve(
            "test.py", snippet_orig, snippet_new,
        )
        assert actual_orig == full_file
        assert "# header\n" in full_new
        assert "return 42" in full_new
        assert "# footer\n" in full_new
        assert "    pass" not in full_new

    def test_snippet_not_found_raises(self, repo_dir, resolve):
        """When snippet can't be located, raise 400 instead of silent replace."""
        full_file = "def real_function():\n    return 1\n" * 20
        bogus_snippet = "def nonexistent_function():\n    return 999"
        (repo_dir / "test.py").write_text(full_file)

        with pytest.raises(HTTPException) as exc_info:
            resolve("test.py", bogus_snippet, "replacement")
        assert exc_info.value.status_code == 400
        assert "Could not locate" in exc_info.value.detail

    def test_snippet_with_whitespace_variance(self, repo_dir, resolve):
        """Stripped snippet matching — leading/trailing whitespace ignored."""
        full_file = "# header\ndef foo():\n    pass\n# footer\n"
        snippet_orig = "\n  def foo():\n    pass  \n"
        snippet_new = "def foo():\n    return 42"
        (repo_dir / "test.py").write_text(full_file)

        actual_orig, full_new, diff = resolve(
            "test.py", snippet_orig, snippet_new,
        )
        assert "return 42" in full_new
        assert "# header" in full_new

    def test_new_file_no_snippet_check(self, repo_dir, resolve):
        """New files (not on disk) skip snippet matching entirely."""
        actual_orig, full_new, diff = resolve(
            "new_file.py", "", "print('hello')\n",
        )
        assert full_new == "print('hello')\n"
        assert "+print('hello')" in diff


# ---------------------------------------------------------------------------
# _resolve_file: size guard
# ---------------------------------------------------------------------------

class TestResolveFileSizeGuard:
    """The size guard prevents replacing a large file with a small snippet."""

    def test_size_guard_rejects_drastic_shrink(self, repo_dir, resolve):
        """Reject when new content is <20% of original (file > 500 chars)."""
        large_content = "x = 1\n" * 200  # 1200 chars
        small_replacement = "x = 1\n"     # 6 chars
        (repo_dir / "big.py").write_text(large_content)

        with pytest.raises(HTTPException) as exc_info:
            resolve("big.py", large_content, small_replacement)
        assert exc_info.value.status_code == 400
        assert "looks like a snippet" in exc_info.value.detail

    def test_size_guard_allows_reasonable_shrink(self, repo_dir, resolve):
        """A 50% reduction should be fine."""
        original = "line\n" * 200   # 1000 chars
        new = "line\n" * 100       # 500 chars — 50%
        (repo_dir / "file.py").write_text(original)

        actual_orig, full_new, diff = resolve("file.py", original, new)
        assert full_new == new

    def test_size_guard_skips_small_files(self, repo_dir, resolve):
        """Files <=500 chars bypass the size guard."""
        original = "short\n" * 10   # 60 chars
        new = "x\n"                 # 2 chars
        (repo_dir / "tiny.py").write_text(original)

        actual_orig, full_new, diff = resolve("tiny.py", original, new)
        assert full_new == new

    def test_size_guard_allows_growth(self, repo_dir, resolve):
        """Growing a file should never trigger the guard."""
        original = "x = 1\n" * 100
        new = "x = 1\n" * 300
        (repo_dir / "file.py").write_text(original)

        actual_orig, full_new, diff = resolve("file.py", original, new)
        assert full_new == new


# ---------------------------------------------------------------------------
# _resolve_file: the exact scenario that corrupted bot.py
# ---------------------------------------------------------------------------

class TestBotPyCorruptionScenario:
    """Reproduce the exact bug that destroyed herald/bot.py."""

    def test_snippet_as_original_with_unrelated_new_content(self, repo_dir, resolve):
        """
        Agent sends original_content (122 lines) not found in 752-line file.
        Must raise 400, not silently replace.
        """
        real_bot_py = "\n".join(
            [f"# line {i}: real bot code" for i in range(752)]
        ) + "\n"
        (repo_dir / "bot.py").write_text(real_bot_py)

        agent_original = "\n".join(
            [f"# line {i}: agent hallucinated code" for i in range(122)]
        )
        agent_new = "\n".join(
            [f"# line {i}: agent replacement code" for i in range(122)]
        )

        with pytest.raises(HTTPException) as exc_info:
            resolve("bot.py", agent_original, agent_new)
        assert exc_info.value.status_code == 400

    def test_snippet_replacement_much_smaller_than_original(self, repo_dir, resolve):
        """
        Even if the snippet somehow matched, the size guard catches it:
        replacing a 752-line file with 122 lines (~15% of original).
        """
        real_content = "real code line\n" * 752  # ~11k chars
        small_new = "new code line\n" * 122      # ~1.7k chars — 15%

        (repo_dir / "bot.py").write_text(real_content)

        with pytest.raises(HTTPException) as exc_info:
            resolve("bot.py", real_content, small_new)
        assert exc_info.value.status_code == 400
        assert "looks like a snippet" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Multi-file proposal creation (integration with DB)
# ---------------------------------------------------------------------------

class TestMultiFileProposals:
    """Test creating proposals with multiple files via the endpoint logic."""

    def test_multi_file_creates_per_file_rows(self, setup_api):
        """A multi-file proposal should create one proposal_files row per file."""
        repo_dir = setup_api
        (repo_dir / "a.py").write_text("old_a\n")
        (repo_dir / "b.py").write_text("old_b\n")

        body = CreateProposalBody(
            title="Multi-file change",
            files=[
                ProposalFile(file_path="a.py", original_content="old_a\n", new_content="new_a\n"),
                ProposalFile(file_path="b.py", original_content="old_b\n", new_content="new_b\n"),
            ],
        )
        result = proposals_mod.create_proposal(body)

        assert result["status"] == "pending"
        assert len(result["files"]) == 2
        assert result["files"][0]["file_path"] == "a.py"
        assert result["files"][1]["file_path"] == "b.py"
        assert set(result["file_paths"]) == {"a.py", "b.py"}

    def test_legacy_single_file_still_works(self, setup_api):
        """Legacy single-file creation (file_path + original + new) still works."""
        repo_dir = setup_api
        (repo_dir / "legacy.py").write_text("old\n")

        body = CreateProposalBody(
            title="Legacy change",
            file_path="legacy.py",
            original_content="old\n",
            new_content="new\n",
        )
        result = proposals_mod.create_proposal(body)

        assert result["status"] == "pending"
        assert len(result["files"]) == 1
        assert result["files"][0]["file_path"] == "legacy.py"

    def test_no_files_raises_400(self, setup_api):
        """Creating a proposal with no files should fail."""
        body = CreateProposalBody(title="Empty")

        with pytest.raises(HTTPException) as exc_info:
            proposals_mod.create_proposal(body)
        assert exc_info.value.status_code == 400
        assert "No files" in exc_info.value.detail

    def test_no_diff_raises_400(self, setup_api):
        """If original == new for all files, no diff → 400."""
        repo_dir = setup_api
        (repo_dir / "same.py").write_text("unchanged\n")

        body = CreateProposalBody(
            title="No change",
            files=[
                ProposalFile(
                    file_path="same.py",
                    original_content="unchanged\n",
                    new_content="unchanged\n",
                ),
            ],
        )

        with pytest.raises(HTTPException) as exc_info:
            proposals_mod.create_proposal(body)
        assert exc_info.value.status_code == 400
        assert "No differences" in exc_info.value.detail

    def test_multi_file_combined_diff(self, setup_api):
        """The parent proposal's diff should contain diffs for all files."""
        repo_dir = setup_api
        (repo_dir / "x.py").write_text("aaa\n")
        (repo_dir / "y.py").write_text("bbb\n")

        body = CreateProposalBody(
            title="Combined diff test",
            files=[
                ProposalFile(file_path="x.py", original_content="aaa\n", new_content="xxx\n"),
                ProposalFile(file_path="y.py", original_content="bbb\n", new_content="yyy\n"),
            ],
        )
        result = proposals_mod.create_proposal(body)

        assert "a/x.py" in result["diff"]
        assert "a/y.py" in result["diff"]
        assert "+xxx" in result["diff"]
        assert "+yyy" in result["diff"]

    def test_snippet_rejection_in_multi_file(self, setup_api):
        """If one file in a multi-file proposal has a bad snippet, the whole thing fails."""
        repo_dir = setup_api
        (repo_dir / "good.py").write_text("old_good\n")
        (repo_dir / "bad.py").write_text("real content\n" * 100)

        body = CreateProposalBody(
            title="Partial bad",
            files=[
                ProposalFile(
                    file_path="good.py",
                    original_content="old_good\n",
                    new_content="new_good\n",
                ),
                ProposalFile(
                    file_path="bad.py",
                    original_content="nonexistent snippet\n",
                    new_content="replacement\n",
                ),
            ],
        )

        with pytest.raises(HTTPException) as exc_info:
            proposals_mod.create_proposal(body)
        assert exc_info.value.status_code == 400
        assert "Could not locate" in exc_info.value.detail
