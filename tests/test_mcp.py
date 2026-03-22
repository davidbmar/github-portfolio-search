"""Unit tests for the MCP server (ghps.mcp_server)."""

from __future__ import annotations

import json
import math
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ghps.mcp_server import TOOLS, handle_message
from ghps.store import EMBEDDING_DIM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_embedding(seed: int) -> list[float]:
    return [math.sin(seed * 0.1 + i * 0.01) * 0.5 for i in range(EMBEDDING_DIM)]


class FakeEmbedder:
    """Minimal embedder stub that returns deterministic vectors."""

    def embed_text(self, text: str) -> list[float]:
        return _fake_embedding(hash(text) % 1000)


MOCK_REPOS = [
    {
        "name": "ml-pipeline",
        "description": "Machine learning data pipeline",
        "language": "Python",
        "topics": ["machine-learning", "data"],
        "stars": 120,
        "updated_at": "2025-06-01",
        "url": "https://github.com/user/ml-pipeline",
    },
    {
        "name": "web-dashboard",
        "description": "React dashboard for monitoring",
        "language": "JavaScript",
        "topics": ["react", "dashboard"],
        "stars": 45,
        "updated_at": "2025-05-15",
        "url": "https://github.com/user/web-dashboard",
    },
]

MOCK_CHUNKS = [
    {"repo_name": "ml-pipeline", "source": "README", "text": "A machine learning pipeline for data processing and model training"},
    {"repo_name": "ml-pipeline", "source": "pipeline.py", "text": "import sklearn pandas numpy data preprocessing"},
    {"repo_name": "web-dashboard", "source": "README", "text": "React dashboard with charts and real-time monitoring"},
    {"repo_name": "web-dashboard", "source": "App.jsx", "text": "export default function Dashboard components hooks"},
]

MOCK_EMBEDDINGS = [_fake_embedding(i) for i in range(len(MOCK_CHUNKS))]


@pytest.fixture
def mcp_store():
    """In-memory VectorStore pre-loaded with test data."""
    from ghps.store import VectorStore

    store = VectorStore(":memory:")
    store.create_index()

    repo_chunks: dict = {}
    repo_embeds: dict = {}
    for chunk, embed in zip(MOCK_CHUNKS, MOCK_EMBEDDINGS):
        rn = chunk["repo_name"]
        repo_chunks.setdefault(rn, []).append(chunk)
        repo_embeds.setdefault(rn, []).append(embed)

    for repo in MOCK_REPOS:
        name = repo["name"]
        store.add_repo(
            repo_dict=repo,
            readme_text="",
            source_files=[],
            embeddings=repo_embeds.get(name, []),
            chunks=repo_chunks.get(name, []),
        )

    yield store
    store.close()


@pytest.fixture
def embedder():
    return FakeEmbedder()


# ---------------------------------------------------------------------------
# Tests: tool definitions
# ---------------------------------------------------------------------------

class TestToolDefinitions:
    def test_tool_count(self):
        assert len(TOOLS) == 4

    def test_tool_names(self):
        names = {t["name"] for t in TOOLS}
        assert names == {
            "portfolio_search",
            "portfolio_clusters",
            "portfolio_repo_detail",
            "portfolio_reindex",
        }

    def test_tools_have_schemas(self):
        for tool in TOOLS:
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_tools_have_descriptions(self):
        for tool in TOOLS:
            assert "description" in tool
            assert len(tool["description"]) > 10


# ---------------------------------------------------------------------------
# Tests: MCP protocol
# ---------------------------------------------------------------------------

class TestMCPProtocol:
    def test_initialize(self, mcp_store, embedder):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = handle_message(msg, mcp_store, embedder)
        assert resp["id"] == 1
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert "tools" in resp["result"]["capabilities"]
        assert resp["result"]["serverInfo"]["name"] == "ghps-mcp"

    def test_tools_list(self, mcp_store, embedder):
        msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = handle_message(msg, mcp_store, embedder)
        assert resp["id"] == 2
        tools = resp["result"]["tools"]
        assert len(tools) == 4
        names = {t["name"] for t in tools}
        assert "portfolio_search" in names
        assert "portfolio_clusters" in names
        assert "portfolio_repo_detail" in names
        assert "portfolio_reindex" in names

    def test_ping(self, mcp_store, embedder):
        msg = {"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {}}
        resp = handle_message(msg, mcp_store, embedder)
        assert resp["id"] == 3
        assert resp["result"] == {}

    def test_notifications_initialized_returns_none(self, mcp_store, embedder):
        msg = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        resp = handle_message(msg, mcp_store, embedder)
        assert resp is None

    def test_unknown_method(self, mcp_store, embedder):
        msg = {"jsonrpc": "2.0", "id": 99, "method": "nonexistent", "params": {}}
        resp = handle_message(msg, mcp_store, embedder)
        assert "error" in resp
        assert resp["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Tests: portfolio_search
# ---------------------------------------------------------------------------

class TestPortfolioSearch:
    def test_search_returns_results(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "portfolio_search",
                "arguments": {"query": "machine learning", "top_k": 5},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        assert resp["id"] == 10
        content = resp["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        results = json.loads(content[0]["text"])
        assert isinstance(results, list)
        assert len(results) > 0
        first = results[0]
        assert "repo_name" in first
        assert "score" in first
        assert "snippet" in first
        assert "url" in first

    def test_search_empty_query_is_error(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "portfolio_search",
                "arguments": {"query": ""},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        assert resp["result"].get("isError") is True

    def test_search_ranked_results(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "portfolio_search",
                "arguments": {"query": "data pipeline", "top_k": 10},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        results = json.loads(resp["result"]["content"][0]["text"])
        if len(results) >= 2:
            assert results[0]["score"] >= results[1]["score"]


# ---------------------------------------------------------------------------
# Tests: portfolio_clusters
# ---------------------------------------------------------------------------

class TestPortfolioClusters:
    def test_clusters_returns_list(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "portfolio_clusters",
                "arguments": {},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        content = resp["result"]["content"]
        clusters = json.loads(content[0]["text"])
        assert isinstance(clusters, list)
        for c in clusters:
            assert "name" in c
            assert "repos" in c
            assert isinstance(c["repos"], list)


# ---------------------------------------------------------------------------
# Tests: portfolio_repo_detail
# ---------------------------------------------------------------------------

class TestPortfolioRepoDetail:
    def test_detail_returns_metadata(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {
                "name": "portfolio_repo_detail",
                "arguments": {"repo_name": "ml-pipeline"},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        detail = json.loads(resp["result"]["content"][0]["text"])
        assert detail["name"] == "ml-pipeline"
        assert detail["language"] == "Python"
        assert detail["stars"] == 120
        assert "url" in detail
        assert "readme_excerpt" in detail
        assert "tech_stack" in detail
        assert "topics" in detail

    def test_detail_not_found(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 31,
            "method": "tools/call",
            "params": {
                "name": "portfolio_repo_detail",
                "arguments": {"repo_name": "nonexistent-repo"},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        assert resp["result"].get("isError") is True

    def test_detail_missing_repo_name(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 32,
            "method": "tools/call",
            "params": {
                "name": "portfolio_repo_detail",
                "arguments": {},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        assert resp["result"].get("isError") is True


# ---------------------------------------------------------------------------
# Tests: portfolio_reindex (error path — no real GitHub client in tests)
# ---------------------------------------------------------------------------

class TestPortfolioReindex:
    def test_reindex_missing_username(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 40,
            "method": "tools/call",
            "params": {
                "name": "portfolio_reindex",
                "arguments": {},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        assert resp["result"].get("isError") is True

    def test_reindex_triggers_indexing(self, mcp_store, embedder, monkeypatch):
        """Test that reindex calls the indexer pipeline (mocked)."""
        called_with = {}

        def fake_fetch_repos(username):
            called_with["username"] = username
            return [
                {
                    "name": "new-repo",
                    "description": "A new repo",
                    "language": "Python",
                    "topics": [],
                    "stars": 1,
                    "updated_at": "2025-01-01",
                    "html_url": "https://github.com/testuser/new-repo",
                }
            ]

        def fake_fetch_readme(owner, repo):
            return "# New Repo\nHello world"

        def fake_fetch_top_files(owner, repo):
            return []

        import ghps.github_client as gc
        monkeypatch.setattr(gc, "fetch_repos", fake_fetch_repos)
        monkeypatch.setattr(gc, "fetch_readme", fake_fetch_readme)
        monkeypatch.setattr(gc, "fetch_top_files", fake_fetch_top_files)

        msg = {
            "jsonrpc": "2.0",
            "id": 41,
            "method": "tools/call",
            "params": {
                "name": "portfolio_reindex",
                "arguments": {"username": "testuser"},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        result = json.loads(resp["result"]["content"][0]["text"])
        assert result["username"] == "testuser"
        assert result["chunks_indexed"] >= 0
        assert called_with["username"] == "testuser"


# ---------------------------------------------------------------------------
# Tests: unknown tool
# ---------------------------------------------------------------------------

class TestUnknownTool:
    def test_unknown_tool_returns_error(self, mcp_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 50,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {},
            },
        }
        resp = handle_message(msg, mcp_store, embedder)
        assert "error" in resp
        assert resp["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Tests: no-index / empty-store edge cases
# ---------------------------------------------------------------------------

class TestNoIndex:
    """Verify MCP tools handle an empty store (no repos indexed)."""

    @pytest.fixture
    def empty_store(self):
        from ghps.store import VectorStore
        store = VectorStore(":memory:")
        store.create_index()
        yield store
        store.close()

    def test_search_empty_store(self, empty_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 60,
            "method": "tools/call",
            "params": {
                "name": "portfolio_search",
                "arguments": {"query": "anything"},
            },
        }
        resp = handle_message(msg, empty_store, embedder)
        content = resp["result"]["content"]
        results = json.loads(content[0]["text"])
        # MCP returns an error dict when no index exists, or an empty list
        assert isinstance(results, (list, dict))
        if isinstance(results, list):
            assert len(results) == 0
        else:
            assert "error" in results

    def test_repo_detail_empty_store(self, empty_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 61,
            "method": "tools/call",
            "params": {
                "name": "portfolio_repo_detail",
                "arguments": {"repo_name": "nonexistent"},
            },
        }
        resp = handle_message(msg, empty_store, embedder)
        assert resp["result"].get("isError") is True

    def test_clusters_empty_store(self, empty_store, embedder):
        msg = {
            "jsonrpc": "2.0",
            "id": 62,
            "method": "tools/call",
            "params": {
                "name": "portfolio_clusters",
                "arguments": {},
            },
        }
        resp = handle_message(msg, empty_store, embedder)
        content = resp["result"]["content"]
        clusters = json.loads(content[0]["text"])
        # MCP returns an error dict when no index exists, or an empty list
        assert isinstance(clusters, (list, dict))
        if isinstance(clusters, list):
            assert len(clusters) == 0
        else:
            assert "error" in clusters
