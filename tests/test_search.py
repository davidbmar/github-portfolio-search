"""Tests for the SearchEngine and CLI."""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from ghps.search import SearchEngine, SearchResult, _recency_boost, _title_boost


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_URLS = {
    "repo-alpha": "https://github.com/user/repo-alpha",
    "repo-beta": "https://github.com/user/repo-beta",
    "repo-gamma": "https://github.com/user/repo-gamma",
}


def _make_mock_store(rows: list[dict], repo_meta: dict | None = None) -> MagicMock:
    """Return a mock VectorStore whose search() returns *rows*.

    *repo_meta* maps repo name to dict with optional keys: url, updated_at.
    Defaults to _REPO_URLS with recent updated_at dates.
    """
    store = MagicMock()
    store.search.return_value = rows

    if repo_meta is None:
        recent = datetime.now(timezone.utc).isoformat()
        repo_meta = {
            name: {"url": url, "updated_at": recent}
            for name, url in _REPO_URLS.items()
        }

    # Mock the connect() call — SearchEngine queries (name, url, updated_at)
    mock_db = MagicMock()
    meta_rows = [
        (name, meta.get("url", ""), meta.get("updated_at", ""))
        for name, meta in repo_meta.items()
    ]
    mock_db.execute.return_value.fetchall.return_value = meta_rows
    store.connect.return_value = mock_db
    return store


def _make_mock_embedder(vector: list[float] | None = None) -> MagicMock:
    """Return a mock EmbeddingPipeline whose embed_text() returns *vector*."""
    embedder = MagicMock()
    embedder.embed_text.return_value = vector or [0.1] * 384
    return embedder


# VectorStore.search() returns distance (lower = more similar)
SAMPLE_ROWS = [
    {
        "repo_name": "repo-alpha",
        "text": "Alpha README content about machine learning pipelines",
        "distance": 0.05,
        "source": "README.md",
    },
    {
        "repo_name": "repo-beta",
        "text": "Beta source code implementing a REST API",
        "distance": 0.12,
        "source": "main.py",
    },
    {
        "repo_name": "repo-alpha",
        "text": "Another chunk from alpha about data processing",
        "distance": 0.18,
        "source": "pipeline.py",
    },
    {
        "repo_name": "repo-gamma",
        "text": "Gamma docs on deployment with Docker",
        "distance": 0.25,
        "source": "README.md",
    },
]


# ---------------------------------------------------------------------------
# SearchEngine tests
# ---------------------------------------------------------------------------

class TestSearchEngine:
    def test_returns_search_results(self):
        store = _make_mock_store(SAMPLE_ROWS)
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("machine learning")

        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    def test_results_sorted_by_score_descending(self):
        store = _make_mock_store(SAMPLE_ROWS)
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("query")

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_deduplicates_repos(self):
        """Only the best-scoring chunk per repo should be kept."""
        store = _make_mock_store(SAMPLE_ROWS)
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("query")

        repo_names = [r.repo_name for r in results]
        assert len(repo_names) == len(set(repo_names)), "Duplicate repos in results"

    def test_dedup_keeps_best_score(self):
        """For repo-alpha, the lowest-distance (0.05) chunk should win.

        Base score = 0.95, recency boost = 1.2 (recent mock date) → 1.14
        """
        store = _make_mock_store(SAMPLE_ROWS)
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("query")

        alpha = next(r for r in results if r.repo_name == "repo-alpha")
        assert alpha.score == pytest.approx(0.95 * 1.2)
        assert alpha.source == "README.md"

    def test_respects_top_k(self):
        store = _make_mock_store(SAMPLE_ROWS)
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("query", top_k=2)

        assert len(results) <= 2

    def test_empty_results(self):
        store = _make_mock_store([])
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("nonexistent topic")

        assert results == []

    def test_embeds_query(self):
        """Verify the query is passed through the embedder."""
        store = _make_mock_store([])
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        engine.search("my specific query")

        embedder.embed_text.assert_called_once_with("my specific query")

    def test_search_result_fields(self):
        store = _make_mock_store(SAMPLE_ROWS[:1])
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("query")

        r = results[0]
        assert r.repo_name == "repo-alpha"
        assert r.chunk_text == "Alpha README content about machine learning pipelines"
        assert r.score == pytest.approx(0.95 * 1.2)  # base * recency boost
        assert r.source == "README.md"
        assert r.repo_url == "https://github.com/user/repo-alpha"


# ---------------------------------------------------------------------------
# Title boosting tests
# ---------------------------------------------------------------------------

class TestTitleBoosting:
    def test_title_boost_matches(self):
        """_title_boost returns 2.0 when query term is in repo name."""
        assert _title_boost("presigned URL", "S3-presignedURL") == 2.0

    def test_title_boost_no_match(self):
        assert _title_boost("machine learning", "repo-alpha") == 1.0

    def test_title_boost_case_insensitive(self):
        assert _title_boost("Voice", "voice-assistant") == 2.0

    def test_presigned_ranks_first(self):
        """Searching 'presigned' should rank a presigned-url repo first."""
        recent = datetime.now(timezone.utc).isoformat()
        repo_meta = {
            "S3-presignedURL": {"url": "https://github.com/user/S3-presignedURL", "updated_at": recent},
            "generic-api": {"url": "https://github.com/user/generic-api", "updated_at": recent},
        }
        rows = [
            {"repo_name": "generic-api", "text": "An API that uses presigned URLs internally", "distance": 0.10, "source": "README.md"},
            {"repo_name": "S3-presignedURL", "text": "S3 presigned URL generation library", "distance": 0.12, "source": "README.md"},
        ]
        store = _make_mock_store(rows, repo_meta=repo_meta)
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("presigned")

        assert results[0].repo_name == "S3-presignedURL"


# ---------------------------------------------------------------------------
# Recency boosting tests
# ---------------------------------------------------------------------------

class TestRecencyBoosting:
    def test_recent_repo_boost(self):
        """Repos updated within 6 months get 1.2x."""
        recent = datetime.now(timezone.utc).isoformat()
        assert _recency_boost(recent) == 1.2

    def test_mid_age_repo_boost(self):
        """Repos updated 6-12 months ago get 1.0x."""
        nine_months_ago = (datetime.now(timezone.utc) - timedelta(days=270)).isoformat()
        assert _recency_boost(nine_months_ago) == 1.0

    def test_old_repo_boost(self):
        """Repos older than 1 year get 0.8x."""
        two_years_ago = (datetime.now(timezone.utc) - timedelta(days=730)).isoformat()
        assert _recency_boost(two_years_ago) == 0.8

    def test_empty_date_gets_penalty(self):
        assert _recency_boost("") == 0.8

    def test_recent_repo_ranked_higher(self):
        """A recent repo should rank higher than a stale one, all else equal."""
        recent = datetime.now(timezone.utc).isoformat()
        stale = (datetime.now(timezone.utc) - timedelta(days=800)).isoformat()
        repo_meta = {
            "fresh-repo": {"url": "https://github.com/user/fresh-repo", "updated_at": recent},
            "stale-repo": {"url": "https://github.com/user/stale-repo", "updated_at": stale},
        }
        rows = [
            {"repo_name": "fresh-repo", "text": "Fresh content about APIs", "distance": 0.15, "source": "README.md"},
            {"repo_name": "stale-repo", "text": "Stale content about APIs", "distance": 0.15, "source": "README.md"},
        ]
        store = _make_mock_store(rows, repo_meta=repo_meta)
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("APIs")

        assert results[0].repo_name == "fresh-repo"
        assert results[1].repo_name == "stale-repo"
        assert results[0].score > results[1].score


# ---------------------------------------------------------------------------
# CLI tests — mock the modules that don't exist on this branch yet
# ---------------------------------------------------------------------------

def _install_fake_modules():
    """Insert mock modules into sys.modules so cli.py's local imports work."""
    mods = {}
    for name in ("ghps.embeddings", "ghps.store", "ghps.indexer", "ghps.github_client"):
        if name not in sys.modules:
            mod = types.ModuleType(name)
            sys.modules[name] = mod
            mods[name] = mod
    return mods


class TestCLI:
    def test_search_command_output(self):
        """CLI search prints formatted results to stdout."""
        fake = _install_fake_modules()
        try:
            mock_store_cls = MagicMock()
            mock_embedder_cls = MagicMock()
            mock_engine_cls = MagicMock()

            mock_results = [
                SearchResult(
                    repo_name="test-repo",
                    chunk_text="Test content for the repo about Python",
                    score=0.91,
                    source="README.md",
                    repo_url="https://github.com/user/test-repo",
                ),
            ]
            mock_engine_cls.return_value.search.return_value = mock_results

            sys.modules["ghps.store"].VectorStore = mock_store_cls
            sys.modules["ghps.embeddings"].EmbeddingPipeline = mock_embedder_cls

            with patch("ghps.search.SearchEngine", mock_engine_cls):
                from click.testing import CliRunner

                # Force reimport to pick up mocked modules
                if "ghps.cli" in sys.modules:
                    del sys.modules["ghps.cli"]
                from ghps.cli import main

                runner = CliRunner()
                result = runner.invoke(main, ["search", "python", "--top-k", "5", "--db", ":memory:"])

                assert result.exit_code == 0, f"CLI failed: {result.output}"
                assert "test-repo" in result.output
                assert "0.9100" in result.output
                assert "README.md" in result.output
        finally:
            for name in fake:
                sys.modules.pop(name, None)
            sys.modules.pop("ghps.cli", None)

    def test_search_no_results(self):
        fake = _install_fake_modules()
        try:
            mock_engine_cls = MagicMock()
            mock_engine_cls.return_value.search.return_value = []

            sys.modules["ghps.store"].VectorStore = MagicMock()
            sys.modules["ghps.embeddings"].EmbeddingPipeline = MagicMock()

            with patch("ghps.search.SearchEngine", mock_engine_cls):
                from click.testing import CliRunner

                if "ghps.cli" in sys.modules:
                    del sys.modules["ghps.cli"]
                from ghps.cli import main

                runner = CliRunner()
                result = runner.invoke(main, ["search", "nonexistent", "--db", ":memory:"])

                assert result.exit_code == 0, f"CLI failed: {result.output}"
                assert "No results found" in result.output
        finally:
            for name in fake:
                sys.modules.pop(name, None)
            sys.modules.pop("ghps.cli", None)

    def test_index_command(self):
        """CLI index triggers indexing for a given username."""
        fake = _install_fake_modules()
        try:
            mock_store_cls = MagicMock()
            mock_embedder_cls = MagicMock()
            mock_indexer_cls = MagicMock()

            sys.modules["ghps.store"].VectorStore = mock_store_cls
            sys.modules["ghps.embeddings"].EmbeddingPipeline = mock_embedder_cls
            sys.modules["ghps.indexer"].Indexer = mock_indexer_cls

            from click.testing import CliRunner

            if "ghps.cli" in sys.modules:
                del sys.modules["ghps.cli"]
            from ghps.cli import main

            runner = CliRunner()
            result = runner.invoke(main, ["index", "testuser", "--db", "/tmp/test.db"])

            assert result.exit_code == 0, f"CLI failed: {result.output}"
            mock_store_cls.assert_called_once_with("/tmp/test.db")
            mock_indexer_cls.assert_called_once()
            mock_indexer_cls.return_value.index_user.assert_called_once()
            call_args = mock_indexer_cls.return_value.index_user.call_args
            assert call_args[0][0] == "testuser"
            assert "Indexing complete" in result.output
        finally:
            for name in fake:
                sys.modules.pop(name, None)
            sys.modules.pop("ghps.cli", None)
