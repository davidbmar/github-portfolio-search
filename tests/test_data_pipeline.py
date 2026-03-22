"""Tests for Sprint 14 data pipeline improvements.

Covers: indexed_at storage, get_index_stats(), freshness calculation, and dry-run mode.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from ghps.search import _freshness_label
from ghps.store import EMBEDDING_DIM, VectorStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store() -> VectorStore:
    store = VectorStore(":memory:")
    store.create_index()
    return store


def _add_test_repo(store: VectorStore, name: str = "test-repo", indexed_at: str | None = None) -> None:
    repo = {
        "name": name,
        "description": "A test repo",
        "language": "Python",
        "topics": ["testing"],
        "stars": 10,
        "updated_at": "2025-06-01",
        "url": f"https://github.com/user/{name}",
    }
    if indexed_at is not None:
        repo["indexed_at"] = indexed_at

    chunks = [{"repo_name": name, "source": "README", "text": "hello world"}]
    embeddings = [[0.1] * EMBEDDING_DIM]
    store.add_repo(repo_dict=repo, readme_text="hello", source_files=[], embeddings=embeddings, chunks=chunks)


# ---------------------------------------------------------------------------
# indexed_at storage tests
# ---------------------------------------------------------------------------

class TestIndexedAt:
    def test_indexed_at_auto_populated(self):
        """indexed_at is automatically set when not provided."""
        store = _make_store()
        _add_test_repo(store, "auto-repo")
        db = store.connect()
        row = db.execute("SELECT indexed_at FROM repos WHERE name = ?", ("auto-repo",)).fetchone()
        assert row[0] is not None
        # Should be a valid ISO timestamp
        dt = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        assert dt.year >= 2025
        store.close()

    def test_indexed_at_explicit_value(self):
        """indexed_at respects explicitly provided values."""
        store = _make_store()
        explicit = "2025-01-15T12:00:00+00:00"
        _add_test_repo(store, "explicit-repo", indexed_at=explicit)
        db = store.connect()
        row = db.execute("SELECT indexed_at FROM repos WHERE name = ?", ("explicit-repo",)).fetchone()
        assert row[0] == explicit
        store.close()

    def test_indexed_at_updated_on_replace(self):
        """indexed_at is updated when a repo is re-indexed (INSERT OR REPLACE)."""
        store = _make_store()
        old_ts = "2024-01-01T00:00:00+00:00"
        new_ts = "2026-01-01T00:00:00+00:00"
        _add_test_repo(store, "replace-repo", indexed_at=old_ts)
        _add_test_repo(store, "replace-repo", indexed_at=new_ts)
        db = store.connect()
        row = db.execute("SELECT indexed_at FROM repos WHERE name = ?", ("replace-repo",)).fetchone()
        assert row[0] == new_ts
        store.close()


# ---------------------------------------------------------------------------
# get_index_stats() tests
# ---------------------------------------------------------------------------

class TestGetIndexStats:
    def test_empty_store(self):
        store = _make_store()
        stats = store.get_index_stats()
        assert stats["total_repos"] == 0
        assert stats["last_indexed"] is None
        assert stats["oldest_repo"] is None
        store.close()

    def test_single_repo(self):
        store = _make_store()
        ts = "2025-06-15T10:00:00+00:00"
        _add_test_repo(store, "only-repo", indexed_at=ts)
        stats = store.get_index_stats()
        assert stats["total_repos"] == 1
        assert stats["last_indexed"] == ts
        assert stats["oldest_repo"] == ts
        store.close()

    def test_multiple_repos(self):
        store = _make_store()
        old_ts = "2024-01-01T00:00:00+00:00"
        new_ts = "2026-03-01T00:00:00+00:00"
        _add_test_repo(store, "old-repo", indexed_at=old_ts)
        _add_test_repo(store, "new-repo", indexed_at=new_ts)
        stats = store.get_index_stats()
        assert stats["total_repos"] == 2
        assert stats["last_indexed"] == new_ts
        assert stats["oldest_repo"] == old_ts
        store.close()


# ---------------------------------------------------------------------------
# Freshness label tests
# ---------------------------------------------------------------------------

class TestFreshnessLabel:
    def test_today(self):
        now = datetime.now(timezone.utc).isoformat()
        assert _freshness_label(now) == "today"

    def test_this_week(self):
        three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        assert _freshness_label(three_days_ago) == "this_week"

    def test_this_month(self):
        two_weeks_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        assert _freshness_label(two_weeks_ago) == "this_month"

    def test_stale(self):
        old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        assert _freshness_label(old) == "stale"

    def test_empty_string(self):
        assert _freshness_label("") == "stale"

    def test_invalid_date(self):
        assert _freshness_label("not-a-date") == "stale"


# ---------------------------------------------------------------------------
# Dry-run mode tests
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_does_not_store(self):
        """Dry-run should not write anything to the store."""
        from ghps.indexer import Indexer

        store = _make_store()
        mock_pipeline = MagicMock()
        mock_pipeline.chunk_text.return_value = ["chunk text"]
        mock_pipeline.embed_batch.return_value = [[0.1] * EMBEDDING_DIM]

        indexer = Indexer(store=store, pipeline=mock_pipeline)
        repos = [
            {
                "name": "dry-repo",
                "description": "Test",
                "language": "Python",
                "topics": [],
                "stars": 0,
                "updated_at": "",
                "url": "",
                "readme": "Some readme content",
                "source_files": [],
            }
        ]

        chunks = indexer.index_repos(repos, dry_run=True)

        assert chunks > 0  # Would have indexed something
        db = store.connect()
        count = db.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
        assert count == 0, "Dry-run should not insert repos"
        store.close()

    def test_dry_run_returns_chunk_count(self):
        """Dry-run should report how many chunks would be indexed."""
        from ghps.indexer import Indexer

        store = _make_store()
        mock_pipeline = MagicMock()
        mock_pipeline.chunk_text.return_value = ["chunk1", "chunk2", "chunk3"]

        indexer = Indexer(store=store, pipeline=mock_pipeline)
        repos = [
            {
                "name": "dry-repo",
                "readme": "Content here",
                "source_files": [],
            }
        ]

        chunks = indexer.index_repos(repos, dry_run=True)
        assert chunks == 3

    def test_normal_run_stores_indexed_at(self):
        """Normal (non-dry-run) indexing should store indexed_at."""
        from ghps.indexer import Indexer

        store = _make_store()
        mock_pipeline = MagicMock()
        mock_pipeline.chunk_text.return_value = ["chunk text"]
        mock_pipeline.embed_batch.return_value = [[0.1] * EMBEDDING_DIM]

        indexer = Indexer(store=store, pipeline=mock_pipeline)
        repos = [
            {
                "name": "real-repo",
                "description": "Test",
                "language": "Python",
                "topics": [],
                "stars": 0,
                "updated_at": "",
                "url": "",
                "readme": "Some readme",
                "source_files": [],
            }
        ]

        indexer.index_repos(repos)

        db = store.connect()
        row = db.execute("SELECT indexed_at FROM repos WHERE name = ?", ("real-repo",)).fetchone()
        assert row[0] is not None
        dt = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        assert dt.year >= 2025
        store.close()


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_failed_repo_does_not_crash_indexer(self):
        """A repo that fails during indexing should be skipped, not crash."""
        from ghps.indexer import Indexer

        store = _make_store()
        mock_pipeline = MagicMock()
        mock_pipeline.chunk_text.return_value = ["chunk text"]
        # First call raises, second call succeeds
        mock_pipeline.embed_batch.side_effect = [
            RuntimeError("embedding failed"),
            [[0.1] * EMBEDDING_DIM],
        ]

        indexer = Indexer(store=store, pipeline=mock_pipeline)
        repos = [
            {"name": "bad-repo", "readme": "content", "source_files": []},
            {"name": "good-repo", "readme": "content", "source_files": []},
        ]

        total = indexer.index_repos(repos)

        # Only the good repo should have been indexed
        assert total == 1
        db = store.connect()
        count = db.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
        assert count == 1
        row = db.execute("SELECT name FROM repos").fetchone()
        assert row[0] == "good-repo"
        store.close()
