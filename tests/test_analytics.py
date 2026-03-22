"""Tests for the analytics module and API analytics endpoints."""

from __future__ import annotations

import os
import tempfile

import pytest

from ghps import analytics


@pytest.fixture
def analytics_db():
    """Provide a temporary analytics DB path, cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_analytics.db")
        yield db_path


# ---------------------------------------------------------------------------
# Unit tests for analytics functions
# ---------------------------------------------------------------------------

class TestLogSearch:
    def test_log_search_creates_record(self, analytics_db):
        analytics.log_search("python ml", 5, "api", db_path=analytics_db)
        recent = analytics.get_recent_queries(limit=10, db_path=analytics_db)
        assert len(recent) == 1
        assert recent[0]["query"] == "python ml"
        assert recent[0]["result_count"] == 5
        assert recent[0]["source"] == "api"

    def test_log_search_multiple(self, analytics_db):
        analytics.log_search("python", 3, "web", db_path=analytics_db)
        analytics.log_search("rust", 1, "cli", db_path=analytics_db)
        analytics.log_search("python", 5, "mcp", db_path=analytics_db)
        recent = analytics.get_recent_queries(limit=10, db_path=analytics_db)
        assert len(recent) == 3

    def test_log_search_stores_timestamp(self, analytics_db):
        analytics.log_search("test", 0, "api", db_path=analytics_db)
        recent = analytics.get_recent_queries(limit=1, db_path=analytics_db)
        assert recent[0]["timestamp"]  # non-empty ISO string


class TestGetPopularQueries:
    def test_popular_queries_ordered_by_count(self, analytics_db):
        for _ in range(3):
            analytics.log_search("popular", 10, "api", db_path=analytics_db)
        analytics.log_search("rare", 2, "web", db_path=analytics_db)

        popular = analytics.get_popular_queries(limit=10, db_path=analytics_db)
        assert len(popular) == 2
        assert popular[0]["query"] == "popular"
        assert popular[0]["count"] == 3
        assert popular[1]["query"] == "rare"
        assert popular[1]["count"] == 1

    def test_popular_queries_respects_limit(self, analytics_db):
        for i in range(5):
            analytics.log_search(f"query-{i}", 1, "api", db_path=analytics_db)
        popular = analytics.get_popular_queries(limit=2, db_path=analytics_db)
        assert len(popular) == 2

    def test_popular_queries_empty_db(self, analytics_db):
        popular = analytics.get_popular_queries(db_path=analytics_db)
        assert popular == []


class TestGetRecentQueries:
    def test_recent_queries_most_recent_first(self, analytics_db):
        analytics.log_search("first", 1, "api", db_path=analytics_db)
        analytics.log_search("second", 2, "web", db_path=analytics_db)
        recent = analytics.get_recent_queries(limit=10, db_path=analytics_db)
        assert recent[0]["query"] == "second"
        assert recent[1]["query"] == "first"

    def test_recent_queries_respects_limit(self, analytics_db):
        for i in range(10):
            analytics.log_search(f"q{i}", 1, "api", db_path=analytics_db)
        recent = analytics.get_recent_queries(limit=3, db_path=analytics_db)
        assert len(recent) == 3

    def test_recent_queries_empty_db(self, analytics_db):
        recent = analytics.get_recent_queries(db_path=analytics_db)
        assert recent == []


class TestGetSearchStats:
    def test_stats_empty_db(self, analytics_db):
        stats = analytics.get_search_stats(db_path=analytics_db)
        assert stats["total_searches"] == 0
        assert stats["unique_queries"] == 0
        assert stats["avg_results"] == 0.0
        assert stats["top_queries"] == []
        assert stats["searches_today"] == 0

    def test_stats_with_data(self, analytics_db):
        analytics.log_search("python", 10, "api", db_path=analytics_db)
        analytics.log_search("python", 10, "web", db_path=analytics_db)
        analytics.log_search("rust", 4, "cli", db_path=analytics_db)

        stats = analytics.get_search_stats(db_path=analytics_db)
        assert stats["total_searches"] == 3
        assert stats["unique_queries"] == 2
        assert stats["avg_results"] == 8.0
        assert stats["searches_today"] == 3
        assert len(stats["top_queries"]) == 2
        assert stats["top_queries"][0]["query"] == "python"

    def test_stats_avg_results_rounded(self, analytics_db):
        analytics.log_search("a", 3, "api", db_path=analytics_db)
        analytics.log_search("b", 7, "api", db_path=analytics_db)
        stats = analytics.get_search_stats(db_path=analytics_db)
        assert stats["avg_results"] == 5.0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestAnalyticsAPIEndpoints:
    """Test the /api/analytics/* endpoints via the real FastAPI app."""

    @pytest.fixture
    def api_client(self, analytics_db, monkeypatch):
        """Build a TestClient against the real api.app with analytics
        pointed at a temp DB."""
        from fastapi.testclient import TestClient
        from ghps import api

        # Redirect analytics to the temp DB
        monkeypatch.setattr(analytics, "_DEFAULT_DB_PATH", analytics_db)

        # We don't need the full lifespan (vector store) for analytics endpoints;
        # save and restore so other tests aren't affected.
        original_lifespan = api.app.router.lifespan_context
        api.app.router.lifespan_context = None  # type: ignore[assignment]
        client = TestClient(api.app, raise_server_exceptions=False)
        yield client
        api.app.router.lifespan_context = original_lifespan

    def test_stats_endpoint_returns_json(self, api_client):
        resp = api_client.get("/api/analytics/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        data = body["data"]
        assert "total_searches" in data
        assert "unique_queries" in data
        assert "avg_results" in data
        assert "top_queries" in data
        assert "searches_today" in data

    def test_stats_endpoint_after_logging(self, api_client, analytics_db):
        analytics.log_search("test query", 5, "api", db_path=analytics_db)
        resp = api_client.get("/api/analytics/stats")
        data = resp.json()["data"]
        assert data["total_searches"] == 1

    def test_queries_endpoint_returns_json(self, api_client):
        resp = api_client.get("/api/analytics/queries")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "queries" in body["data"]

    def test_queries_endpoint_returns_recent(self, api_client, analytics_db):
        analytics.log_search("hello world", 3, "web", db_path=analytics_db)
        resp = api_client.get("/api/analytics/queries")
        queries = resp.json()["data"]["queries"]
        assert len(queries) == 1
        assert queries[0]["query"] == "hello world"
