"""Shared test fixtures for API and integration tests."""

from __future__ import annotations

import json
import math
import sys
import os

import pytest
from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ghps.store import EMBEDDING_DIM


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

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
    {
        "name": "cli-toolkit",
        "description": "Command-line utilities for devops",
        "language": "Go",
        "topics": ["cli", "devops"],
        "stars": 80,
        "updated_at": "2025-04-20",
        "url": "https://github.com/user/cli-toolkit",
    },
]

MOCK_CHUNKS = [
    {"repo_name": "ml-pipeline", "source": "README", "text": "A machine learning pipeline for data processing and model training"},
    {"repo_name": "ml-pipeline", "source": "pipeline.py", "text": "import sklearn pandas numpy data preprocessing"},
    {"repo_name": "web-dashboard", "source": "README", "text": "React dashboard with charts and real-time monitoring"},
    {"repo_name": "web-dashboard", "source": "App.jsx", "text": "export default function Dashboard components hooks"},
    {"repo_name": "cli-toolkit", "source": "README", "text": "Command line tools for kubernetes and docker devops"},
    {"repo_name": "cli-toolkit", "source": "main.go", "text": "package main func cobra cli commands flags"},
]

MOCK_REPOS_BY_NAME = {r["name"]: r for r in MOCK_REPOS}


def _fake_embedding(seed: int) -> list[float]:
    """Generate a deterministic fake embedding vector."""
    return [math.sin(seed * 0.1 + i * 0.01) * 0.5 for i in range(EMBEDDING_DIM)]


MOCK_EMBEDDINGS = [_fake_embedding(i) for i in range(len(MOCK_CHUNKS))]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_store():
    """In-memory SQLite VectorStore pre-loaded with test data.

    Uses check_same_thread=False so the connection works across threads
    (needed for FastAPI's TestClient which runs ASGI in a worker thread).
    """
    from ghps.store import VectorStore, _serialize_f32

    store = VectorStore(":memory:")

    # Monkey-patch connect to pass check_same_thread=False
    _orig_connect = store.connect

    def _patched_connect():
        if store.db is None:
            try:
                import pysqlite3 as sqlite3
            except ImportError:
                import sqlite3
            import sqlite_vec

            store.db = sqlite3.connect(":memory:", check_same_thread=False)
            store.db.enable_load_extension(True)
            sqlite_vec.load(store.db)
            store.db.enable_load_extension(False)
            store.db.row_factory = sqlite3.Row
        return store.db

    store.connect = _patched_connect
    store.create_index()

    # Group chunks/embeddings by repo
    repo_chunks: dict[str, list] = {}
    repo_embeds: dict[str, list] = {}
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
def mock_github_responses():
    """Cached GitHub API-style response dicts for testing."""
    return [
        {
            "name": repo["name"],
            "description": repo["description"],
            "language": repo["language"],
            "topics": repo["topics"],
            "stargazers_count": repo["stars"],
            "updated_at": repo["updated_at"],
            "html_url": repo["url"],
            "readme": f"# {repo['name']}\n\n{repo['description']}",
            "source_files": [
                {"path": "main.py", "content": f"# Source code for {repo['name']}"}
            ],
        }
        for repo in MOCK_REPOS
    ]


# ---------------------------------------------------------------------------
# Minimal FastAPI app (contract stub for agentB's api.py)
#
# This defines the expected API contract. When agentB's real api.py is
# merged, tests can switch to importing that app instead.
# ---------------------------------------------------------------------------

def _build_test_app(store) -> FastAPI:
    """Build a minimal FastAPI app wired to the given store."""
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/search")
    def search(q: str = Query(default=""), limit: int = Query(default=10)):
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="query parameter 'q' is required")

        query_vec = _fake_embedding(hash(q) % 1000)
        raw = store.search(query_vec, limit=limit)

        db = store.connect()
        results = []
        for row in raw:
            repo_row = db.execute(
                "SELECT * FROM repos WHERE name = ?", (row["repo_name"],)
            ).fetchone()
            results.append({
                "repo_name": row["repo_name"],
                "text": row["text"],
                "source": row["source"],
                "distance": row["distance"],
                "url": repo_row["url"] if repo_row else "",
            })
        return {"results": results}

    @app.get("/api/clusters")
    def clusters():
        db = store.connect()
        rows = db.execute(
            "SELECT DISTINCT language FROM repos WHERE language IS NOT NULL AND language != ''"
        ).fetchall()
        cluster_list = [{"language": row[0], "count": 1} for row in rows]
        return {"clusters": cluster_list}

    @app.get("/api/repos/{slug}")
    def repo_detail(slug: str):
        db = store.connect()
        row = db.execute("SELECT * FROM repos WHERE name = ?", (slug,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Repo '{slug}' not found")
        return {
            "name": row["name"],
            "description": row["description"],
            "language": row["language"],
            "topics": json.loads(row["topics"]) if row["topics"] else [],
            "stars": row["stars"],
            "updated_at": row["updated_at"],
            "url": row["url"],
        }

    return app


@pytest.fixture
def test_app(mock_store):
    """FastAPI app wired to the mock store."""
    return _build_test_app(mock_store)


@pytest.fixture
def client(test_app):
    """FastAPI TestClient for making HTTP requests without a server."""
    return TestClient(test_app)
