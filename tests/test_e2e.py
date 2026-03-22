"""End-to-end test: create temp index, index mock repos, search, verify, clean up."""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from ghps.store import VectorStore, EMBEDDING_DIM
from ghps.search import SearchEngine, SearchResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_REPOS = [
    {
        "name": "data-pipeline",
        "description": "ETL pipeline for processing large datasets",
        "language": "Python",
        "topics": ["data", "etl", "pipeline"],
        "stars": 50,
        "updated_at": "2025-06-01",
        "url": "https://github.com/user/data-pipeline",
    },
    {
        "name": "react-app",
        "description": "Frontend web application built with React",
        "language": "JavaScript",
        "topics": ["react", "frontend", "web"],
        "stars": 30,
        "updated_at": "2025-05-15",
        "url": "https://github.com/user/react-app",
    },
]


@pytest.fixture
def temp_db():
    """Create a temporary database file, clean up after test."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="ghps_e2e_")
    os.close(fd)
    os.unlink(path)  # VectorStore will create it
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def populated_store(temp_db):
    """Create a VectorStore with mock data indexed."""
    from ghps.embeddings import EmbeddingPipeline

    pipeline = EmbeddingPipeline()
    store = VectorStore(temp_db)
    store.create_index()

    for repo in MOCK_REPOS:
        readme = f"# {repo['name']}\n\n{repo['description']}\n\nThis is a {repo['language']} project."
        chunks_text = pipeline.chunk_text(readme)
        if not chunks_text:
            chunks_text = [readme]

        chunks = [
            {"repo_name": repo["name"], "source": "README", "text": t}
            for t in chunks_text
        ]
        embeddings = pipeline.embed_batch(chunks_text)

        store.add_repo(
            repo_dict=repo,
            readme_text=readme,
            source_files=[],
            embeddings=embeddings,
            chunks=chunks,
        )

    yield store
    store.close()


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_index_then_search(self, populated_store):
        """Index mock repos, then search and verify results are returned."""
        from ghps.embeddings import EmbeddingPipeline

        engine = SearchEngine(populated_store, EmbeddingPipeline())
        results = engine.search("data processing pipeline", top_k=5)

        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        # data-pipeline should score highest for this query
        assert results[0].repo_name == "data-pipeline"
        assert results[0].score > 0

    def test_search_returns_correct_repo(self, populated_store):
        """Search for React should return react-app."""
        from ghps.embeddings import EmbeddingPipeline

        engine = SearchEngine(populated_store, EmbeddingPipeline())
        results = engine.search("React frontend web application", top_k=5)

        assert len(results) > 0
        repo_names = [r.repo_name for r in results]
        assert "react-app" in repo_names

    def test_results_are_deduplicated(self, populated_store):
        """Each repo should appear at most once in results."""
        from ghps.embeddings import EmbeddingPipeline

        engine = SearchEngine(populated_store, EmbeddingPipeline())
        results = engine.search("project", top_k=10)

        repo_names = [r.repo_name for r in results]
        assert len(repo_names) == len(set(repo_names))

    def test_results_sorted_by_score(self, populated_store):
        """Results should be sorted by score descending."""
        from ghps.embeddings import EmbeddingPipeline

        engine = SearchEngine(populated_store, EmbeddingPipeline())
        results = engine.search("project", top_k=10)

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_cli_search_e2e(self, populated_store, temp_db):
        """Test the full CLI search command end-to-end."""
        from unittest.mock import patch
        from ghps.embeddings import EmbeddingPipeline

        # Patch _db_exists since temp file exists
        with patch("ghps.cli._db_exists", return_value=True):
            import sys
            sys.modules.pop("ghps.cli", None)
            from ghps.cli import main

            runner = CliRunner()
            result = runner.invoke(main, ["search", "data pipeline", "--db", temp_db])

            assert result.exit_code == 0, f"CLI failed: {result.output}"
            assert "data-pipeline" in result.output

    def test_cli_search_json_e2e(self, populated_store, temp_db):
        """Test the CLI search --format json end-to-end."""
        from unittest.mock import patch

        with patch("ghps.cli._db_exists", return_value=True):
            import sys
            sys.modules.pop("ghps.cli", None)
            from ghps.cli import main

            runner = CliRunner()
            result = runner.invoke(
                main, ["search", "data pipeline", "--db", temp_db, "--format", "json"]
            )

            assert result.exit_code == 0, f"CLI failed: {result.output}"
            data = json.loads(result.output)
            assert isinstance(data, list)
            assert len(data) > 0
            assert data[0]["repo_name"] == "data-pipeline"

    def test_cli_status_e2e(self, populated_store, temp_db):
        """Test the CLI status command end-to-end."""
        from unittest.mock import patch

        with patch("ghps.cli._db_exists", return_value=True):
            import sys
            sys.modules.pop("ghps.cli", None)
            from ghps.cli import main

            runner = CliRunner()
            result = runner.invoke(main, ["status", "--db", temp_db])

            assert result.exit_code == 0, f"CLI failed: {result.output}"
            assert "2" in result.output  # 2 repos
