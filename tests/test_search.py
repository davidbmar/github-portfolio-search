"""Tests for the SearchEngine and CLI."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from ghps.search import SearchEngine, SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_store(rows: list[dict]) -> MagicMock:
    """Return a mock VectorStore whose search() returns *rows*."""
    store = MagicMock()
    store.search.return_value = rows
    return store


def _make_mock_embedder(vector: list[float] | None = None) -> MagicMock:
    """Return a mock EmbeddingPipeline whose embed_text() returns *vector*."""
    embedder = MagicMock()
    embedder.embed_text.return_value = vector or [0.1] * 384
    return embedder


SAMPLE_ROWS = [
    {
        "repo_name": "repo-alpha",
        "text": "Alpha README content about machine learning pipelines",
        "score": 0.95,
        "source": "README.md",
        "url": "https://github.com/user/repo-alpha",
    },
    {
        "repo_name": "repo-beta",
        "text": "Beta source code implementing a REST API",
        "score": 0.88,
        "source": "main.py",
        "url": "https://github.com/user/repo-beta",
    },
    {
        "repo_name": "repo-alpha",
        "text": "Another chunk from alpha about data processing",
        "score": 0.82,
        "source": "pipeline.py",
        "url": "https://github.com/user/repo-alpha",
    },
    {
        "repo_name": "repo-gamma",
        "text": "Gamma docs on deployment with Docker",
        "score": 0.75,
        "source": "README.md",
        "url": "https://github.com/user/repo-gamma",
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
        """For repo-alpha, the 0.95 chunk should win over the 0.82 chunk."""
        store = _make_mock_store(SAMPLE_ROWS)
        embedder = _make_mock_embedder()
        engine = SearchEngine(store, embedder)

        results = engine.search("query")

        alpha = next(r for r in results if r.repo_name == "repo-alpha")
        assert alpha.score == 0.95
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
        assert r.score == 0.95
        assert r.source == "README.md"
        assert r.repo_url == "https://github.com/user/repo-alpha"


# ---------------------------------------------------------------------------
# CLI tests — mock the modules that don't exist on this branch yet
# ---------------------------------------------------------------------------

def _install_fake_modules():
    """Insert mock modules into sys.modules so cli.py's local imports work."""
    mods = {}
    for name in ("ghps.embeddings", "ghps.store", "ghps.indexer"):
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
                result = runner.invoke(main, ["search", "python", "--top-k", "5"])

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
                result = runner.invoke(main, ["search", "nonexistent"])

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
            mock_indexer_cls = MagicMock()
            sys.modules["ghps.indexer"].Indexer = mock_indexer_cls

            from click.testing import CliRunner

            if "ghps.cli" in sys.modules:
                del sys.modules["ghps.cli"]
            from ghps.cli import main

            runner = CliRunner()
            result = runner.invoke(main, ["index", "testuser", "--db", "/tmp/test.db"])

            assert result.exit_code == 0, f"CLI failed: {result.output}"
            mock_indexer_cls.assert_called_once_with(db_path="/tmp/test.db")
            mock_indexer_cls.return_value.index_user.assert_called_once_with("testuser")
            assert "Indexing complete" in result.output
        finally:
            for name in fake:
                sys.modules.pop(name, None)
            sys.modules.pop("ghps.cli", None)
