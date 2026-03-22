"""Tests for the REST API endpoints.

Uses FastAPI TestClient (no server needed). The API contract is defined
in conftest.py as a stub; when agentB's real api.py is merged these tests
validate the same contract.
"""

from __future__ import annotations


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_returns_json(self, client):
        resp = client.get("/api/health")
        assert resp.headers["content-type"] == "application/json"


class TestSearchEndpoint:
    def test_search_returns_results(self, client):
        resp = client.get("/api/search", params={"q": "machine learning"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) > 0

    def test_search_result_shape(self, client):
        resp = client.get("/api/search", params={"q": "python"})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) > 0
        first = results[0]
        assert "repo_name" in first
        assert "text" in first
        assert "source" in first

    def test_search_empty_query_returns_error(self, client):
        resp = client.get("/api/search", params={"q": ""})
        assert resp.status_code == 400

    def test_search_missing_query_returns_error(self, client):
        resp = client.get("/api/search")
        assert resp.status_code == 400

    def test_search_respects_limit(self, client):
        resp = client.get("/api/search", params={"q": "code", "limit": 2})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) <= 2

    def test_search_returns_json(self, client):
        resp = client.get("/api/search", params={"q": "test"})
        assert resp.headers["content-type"] == "application/json"


class TestClustersEndpoint:
    def test_clusters_returns_non_empty(self, client):
        resp = client.get("/api/clusters")
        assert resp.status_code == 200
        data = resp.json()
        assert "clusters" in data
        assert len(data["clusters"]) > 0

    def test_clusters_contain_languages(self, client):
        resp = client.get("/api/clusters")
        data = resp.json()
        languages = [c["language"] for c in data["clusters"]]
        assert "Python" in languages
        assert "JavaScript" in languages
        assert "Go" in languages

    def test_clusters_returns_json(self, client):
        resp = client.get("/api/clusters")
        assert resp.headers["content-type"] == "application/json"


class TestRepoDetailEndpoint:
    def test_known_repo_returns_200(self, client):
        resp = client.get("/api/repos/ml-pipeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "ml-pipeline"
        assert data["language"] == "Python"
        assert data["stars"] == 120

    def test_repo_has_expected_fields(self, client):
        resp = client.get("/api/repos/web-dashboard")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("name", "description", "language", "topics", "stars", "url"):
            assert field in data, f"Missing field: {field}"

    def test_repo_topics_are_list(self, client):
        resp = client.get("/api/repos/ml-pipeline")
        data = resp.json()
        assert isinstance(data["topics"], list)
        assert "machine-learning" in data["topics"]

    def test_unknown_repo_returns_404(self, client):
        resp = client.get("/api/repos/nonexistent-repo")
        assert resp.status_code == 404

    def test_unknown_repo_returns_json_error(self, client):
        resp = client.get("/api/repos/nonexistent-repo")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
