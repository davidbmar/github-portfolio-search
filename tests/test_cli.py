"""Tests for the ghps CLI commands using Click CliRunner."""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ghps.search import SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _install_fake_modules():
    """Insert mock modules into sys.modules so cli.py's lazy imports work."""
    mods = {}
    for name in ("ghps.embeddings", "ghps.store", "ghps.indexer", "ghps.github_client"):
        if name not in sys.modules:
            mod = types.ModuleType(name)
            sys.modules[name] = mod
            mods[name] = mod
        else:
            mods[name] = sys.modules[name]
    return mods


def _reload_cli():
    """Force reimport of ghps.cli so it picks up mocked modules."""
    sys.modules.pop("ghps.cli", None)
    from ghps.cli import main
    return main


def _cleanup(fake_mods):
    """Remove fake modules from sys.modules."""
    for name in fake_mods:
        sys.modules.pop(name, None)
    sys.modules.pop("ghps.cli", None)


SAMPLE_RESULTS = [
    SearchResult(
        repo_name="ml-pipeline",
        chunk_text="Machine learning pipeline for data processing and model training with sklearn",
        score=0.92,
        source="README.md",
        repo_url="https://github.com/user/ml-pipeline",
    ),
    SearchResult(
        repo_name="web-dashboard",
        chunk_text="React dashboard with charts and real-time monitoring",
        score=0.65,
        source="App.jsx",
        repo_url="https://github.com/user/web-dashboard",
    ),
]


# ---------------------------------------------------------------------------
# ghps search
# ---------------------------------------------------------------------------

class TestSearchCommand:
    def test_search_shows_results(self):
        fake = _install_fake_modules()
        try:
            mock_store_cls = MagicMock()
            mock_embedder_cls = MagicMock()
            mock_engine_cls = MagicMock()
            mock_engine_cls.return_value.search.return_value = SAMPLE_RESULTS

            sys.modules["ghps.store"].VectorStore = mock_store_cls
            sys.modules["ghps.embeddings"].EmbeddingPipeline = mock_embedder_cls

            with patch("ghps.search.SearchEngine", mock_engine_cls):
                main = _reload_cli()
                runner = CliRunner()
                # Use --db :memory: to bypass _db_exists file check
                result = runner.invoke(main, ["search", "machine learning", "--top-k", "5", "--db", ":memory:"])

                assert result.exit_code == 0, f"CLI failed: {result.output}"
                assert "ml-pipeline" in result.output
                assert "0.9200" in result.output
                assert "README.md" in result.output
                assert "web-dashboard" in result.output
        finally:
            _cleanup(fake)

    def test_search_no_results(self):
        fake = _install_fake_modules()
        try:
            mock_engine_cls = MagicMock()
            mock_engine_cls.return_value.search.return_value = []

            sys.modules["ghps.store"].VectorStore = MagicMock()
            sys.modules["ghps.embeddings"].EmbeddingPipeline = MagicMock()

            with patch("ghps.search.SearchEngine", mock_engine_cls):
                main = _reload_cli()
                runner = CliRunner()
                result = runner.invoke(main, ["search", "nonexistent", "--db", ":memory:"])

                assert result.exit_code == 0, f"CLI failed: {result.output}"
                assert "No results found" in result.output
        finally:
            _cleanup(fake)

    def test_search_json_format(self):
        fake = _install_fake_modules()
        try:
            mock_engine_cls = MagicMock()
            mock_engine_cls.return_value.search.return_value = SAMPLE_RESULTS

            sys.modules["ghps.store"].VectorStore = MagicMock()
            sys.modules["ghps.embeddings"].EmbeddingPipeline = MagicMock()

            with patch("ghps.search.SearchEngine", mock_engine_cls):
                main = _reload_cli()
                runner = CliRunner()
                result = runner.invoke(main, ["search", "query", "--format", "json", "--db", ":memory:"])

                assert result.exit_code == 0, f"CLI failed: {result.output}"
                data = json.loads(result.output)
                assert isinstance(data, list)
                assert len(data) == 2
                assert data[0]["repo_name"] == "ml-pipeline"
                assert data[0]["score"] == 0.92
                assert "snippet" in data[0]
        finally:
            _cleanup(fake)

    def test_search_missing_index(self):
        """Search should fail with a helpful message when the DB doesn't exist."""
        sys.modules.pop("ghps.cli", None)
        from ghps.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["search", "query", "--db", "/nonexistent/path.db"])

        assert result.exit_code != 0
        assert "Index not found" in result.output

        sys.modules.pop("ghps.cli", None)

    def test_search_colored_scores(self):
        """High scores should show green, medium yellow — score values appear in output."""
        fake = _install_fake_modules()
        try:
            mock_engine_cls = MagicMock()
            mock_engine_cls.return_value.search.return_value = SAMPLE_RESULTS

            sys.modules["ghps.store"].VectorStore = MagicMock()
            sys.modules["ghps.embeddings"].EmbeddingPipeline = MagicMock()

            with patch("ghps.search.SearchEngine", mock_engine_cls):
                main = _reload_cli()
                runner = CliRunner()
                result = runner.invoke(main, ["search", "query", "--db", ":memory:"])

                assert result.exit_code == 0
                assert "0.9200" in result.output
                assert "0.6500" in result.output
        finally:
            _cleanup(fake)


# ---------------------------------------------------------------------------
# ghps index
# ---------------------------------------------------------------------------

class TestIndexCommand:
    def test_index_triggers_indexing(self):
        fake = _install_fake_modules()
        try:
            mock_store_cls = MagicMock()
            mock_embedder_cls = MagicMock()
            mock_indexer_cls = MagicMock()

            sys.modules["ghps.store"].VectorStore = mock_store_cls
            sys.modules["ghps.embeddings"].EmbeddingPipeline = mock_embedder_cls
            sys.modules["ghps.indexer"].Indexer = mock_indexer_cls

            main = _reload_cli()
            runner = CliRunner()
            result = runner.invoke(main, ["index", "testuser", "--db", "/tmp/test_ghps.db"])

            assert result.exit_code == 0, f"CLI failed: {result.output}"
            mock_store_cls.assert_called_once_with("/tmp/test_ghps.db")
            mock_indexer_cls.assert_called_once()
            mock_indexer_cls.return_value.index_user.assert_called_once()
            call_args = mock_indexer_cls.return_value.index_user.call_args
            assert call_args[0][0] == "testuser"
            assert "Indexing complete" in result.output
        finally:
            _cleanup(fake)

    def test_index_with_token(self):
        fake = _install_fake_modules()
        try:
            mock_store_cls = MagicMock()
            mock_embedder_cls = MagicMock()
            mock_indexer_cls = MagicMock()

            sys.modules["ghps.store"].VectorStore = mock_store_cls
            sys.modules["ghps.embeddings"].EmbeddingPipeline = mock_embedder_cls
            sys.modules["ghps.indexer"].Indexer = mock_indexer_cls

            main = _reload_cli()
            runner = CliRunner(env={"GITHUB_TOKEN": ""})
            result = runner.invoke(
                main, ["index", "testuser", "--db", "/tmp/test_ghps.db", "--token", "ghp_test123"]
            )

            assert result.exit_code == 0, f"CLI failed: {result.output}"
        finally:
            _cleanup(fake)


# ---------------------------------------------------------------------------
# ghps status
# ---------------------------------------------------------------------------

class TestStatusCommand:
    def test_status_shows_stats(self):
        fake = _install_fake_modules()
        try:
            mock_store_cls = MagicMock()
            mock_db = MagicMock()
            mock_store_cls.return_value.connect.return_value = mock_db
            mock_db.execute.side_effect = lambda sql, *args: _mock_status_execute(sql)

            sys.modules["ghps.store"].VectorStore = mock_store_cls

            main = _reload_cli()
            # Patch _db_exists on the already-imported module
            import ghps.cli as cli_mod
            with patch.object(cli_mod, "_db_exists", return_value=True):
                runner = CliRunner()
                result = runner.invoke(main, ["status"])

                assert result.exit_code == 0, f"CLI failed: {result.output}"
                assert "5" in result.output  # repo count
                assert "42" in result.output  # chunk count
                assert "2025-06-01" in result.output  # last indexed
        finally:
            _cleanup(fake)

    def test_status_json_format(self):
        fake = _install_fake_modules()
        try:
            mock_store_cls = MagicMock()
            mock_db = MagicMock()
            mock_store_cls.return_value.connect.return_value = mock_db
            mock_db.execute.side_effect = lambda sql, *args: _mock_status_execute(sql)

            sys.modules["ghps.store"].VectorStore = mock_store_cls

            main = _reload_cli()
            import ghps.cli as cli_mod
            with patch.object(cli_mod, "_db_exists", return_value=True):
                runner = CliRunner()
                result = runner.invoke(main, ["status", "--format", "json"])

                assert result.exit_code == 0, f"CLI failed: {result.output}"
                data = json.loads(result.output)
                assert data["repo_count"] == 5
                assert data["chunk_count"] == 42
                assert data["last_indexed"] == "2025-06-01"
        finally:
            _cleanup(fake)

    def test_status_missing_index(self):
        """Status should fail with a helpful message when the DB doesn't exist."""
        sys.modules.pop("ghps.cli", None)
        from ghps.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["status", "--db", "/nonexistent/path.db"])

        assert result.exit_code != 0
        assert "Index not found" in result.output

        sys.modules.pop("ghps.cli", None)


def _mock_status_execute(sql: str) -> MagicMock:
    """Return mock cursor results for status command queries."""
    mock_cursor = MagicMock()
    if "COUNT(*) FROM repos" in sql:
        mock_cursor.fetchone.return_value = (5,)
    elif "COUNT(*) FROM chunks" in sql:
        mock_cursor.fetchone.return_value = (42,)
    elif "updated_at" in sql:
        mock_cursor.fetchone.return_value = ("2025-06-01",)
    else:
        mock_cursor.fetchone.return_value = None
    return mock_cursor


# ---------------------------------------------------------------------------
# ghps serve
# ---------------------------------------------------------------------------

class TestServeCommand:
    def test_serve_missing_index(self):
        """Serve should fail with a helpful message when the DB doesn't exist."""
        sys.modules.pop("ghps.cli", None)
        from ghps.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["serve", "--db", "/nonexistent/path.db"])

        assert result.exit_code != 0
        assert "Index not found" in result.output

        sys.modules.pop("ghps.cli", None)
