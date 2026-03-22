"""Tests for graceful error handling when no index exists (B-008/B-016).

Verifies that /api/search, /api/clusters, and /api/repos/<slug> return
200 with {"results": [], "error": "..."} instead of 500 when the
SQLite index tables are missing.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def no_index_client(tmp_path):
    """TestClient using the real api.py app with an empty database (no tables)."""
    import ghps.api as api_module

    # Point the app at a fresh empty database (no create_index call)
    empty_db = str(tmp_path / "empty.db")
    api_module.app.state.db_path = empty_db

    # Mock the EmbeddingPipeline to avoid loading the model
    mock_embedder = MagicMock()
    mock_embedder.embed_text.return_value = [0.0] * 384

    with patch.object(api_module, "EmbeddingPipeline", return_value=mock_embedder):
        with TestClient(api_module.app, raise_server_exceptions=False) as client:
            yield client


class TestNoIndexSearch:
    def test_search_returns_200_with_empty_results(self, no_index_client):
        resp = no_index_client.get("/api/search", params={"q": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert "error" in data
        assert "No index found" in data["error"]

    def test_search_error_message_suggests_fix(self, no_index_client):
        resp = no_index_client.get("/api/search", params={"q": "anything"})
        data = resp.json()
        assert "ghps index" in data["error"]


class TestNoIndexClusters:
    def test_clusters_returns_200_with_empty_results(self, no_index_client):
        resp = no_index_client.get("/api/clusters")
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert "error" in data
        assert "No index found" in data["error"]


class TestNoIndexRepoDetail:
    def test_repo_detail_returns_200_with_empty_results(self, no_index_client):
        resp = no_index_client.get("/api/repos/some-repo")
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert "error" in data
        assert "No index found" in data["error"]
