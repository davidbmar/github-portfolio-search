"""Tests for the vector store."""

from __future__ import annotations

from ghps.store import VectorStore, _serialize_f32, EMBEDDING_DIM


class TestVectorStoreSchema:
    def test_create_index(self):
        store = VectorStore(":memory:")
        store.create_index()
        db = store.connect()
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "repos" in tables
        assert "chunks" in tables
        assert "repo_files" in tables
        assert "vec_chunks" in tables
        store.close()

    def test_create_index_idempotent(self):
        store = VectorStore(":memory:")
        store.create_index()
        store.create_index()  # Should not raise
        store.close()


class TestAddRepo:
    def _make_store(self):
        store = VectorStore(":memory:")
        store.create_index()
        return store

    def test_add_repo_stores_metadata(self):
        store = self._make_store()
        repo = {
            "name": "test-repo",
            "description": "A test repo",
            "language": "Python",
            "topics": ["testing", "demo"],
            "stars": 42,
            "updated_at": "2025-01-01",
            "url": "https://github.com/user/test-repo",
        }
        chunks = [{"repo_name": "test-repo", "source": "README", "text": "hello world"}]
        fake_embedding = [0.1] * EMBEDDING_DIM

        store.add_repo(
            repo_dict=repo,
            readme_text="hello world",
            source_files=[],
            embeddings=[fake_embedding],
            chunks=chunks,
        )

        db = store.connect()
        row = db.execute("SELECT * FROM repos WHERE name = ?", ("test-repo",)).fetchone()
        assert row is not None
        assert row["description"] == "A test repo"
        assert row["stars"] == 42
        store.close()

    def test_add_repo_stores_chunks(self):
        store = self._make_store()
        repo = {"name": "test-repo"}
        chunks = [
            {"repo_name": "test-repo", "source": "README", "text": "chunk one"},
            {"repo_name": "test-repo", "source": "main.py", "text": "chunk two"},
        ]
        embeddings = [[0.1] * EMBEDDING_DIM, [0.2] * EMBEDDING_DIM]

        store.add_repo(
            repo_dict=repo,
            readme_text="readme",
            source_files=[{"path": "main.py", "content": "code"}],
            embeddings=embeddings,
            chunks=chunks,
        )

        db = store.connect()
        rows = db.execute("SELECT * FROM chunks").fetchall()
        assert len(rows) == 2
        store.close()

    def test_add_repo_stores_files(self):
        store = self._make_store()
        repo = {"name": "test-repo"}
        store.add_repo(
            repo_dict=repo,
            readme_text="",
            source_files=[{"path": "app.py", "content": "print('hi')"}],
            embeddings=[],
            chunks=[],
        )

        db = store.connect()
        rows = db.execute("SELECT * FROM repo_files").fetchall()
        assert len(rows) == 1
        assert rows[0]["path"] == "app.py"
        store.close()


class TestSearch:
    def test_search_returns_results(self):
        store = VectorStore(":memory:")
        store.create_index()

        repo = {"name": "myrepo"}
        chunks = [
            {"repo_name": "myrepo", "source": "README", "text": "python machine learning library"},
            {"repo_name": "myrepo", "source": "README", "text": "cooking recipes for dinner"},
        ]
        # Use fake but distinct embeddings (normalised unit-ish vectors)
        import math
        dim = EMBEDDING_DIM
        emb1 = [1.0 / math.sqrt(dim)] * dim
        emb2 = [-1.0 / math.sqrt(dim)] * dim

        store.add_repo(
            repo_dict=repo,
            readme_text="",
            source_files=[],
            embeddings=[emb1, emb2],
            chunks=chunks,
        )

        # Query with emb1-like vector — should match first chunk (smaller distance)
        results = store.search(emb1, limit=2)
        assert len(results) == 2
        assert results[0]["text"] == "python machine learning library"

    def test_search_empty_store(self):
        store = VectorStore(":memory:")
        store.create_index()
        query_vec = [0.0] * EMBEDDING_DIM
        results = store.search(query_vec, limit=5)
        assert results == []

    def test_search_respects_limit(self):
        store = VectorStore(":memory:")
        store.create_index()

        repo = {"name": "myrepo"}
        chunks = [
            {"repo_name": "myrepo", "source": "README", "text": f"chunk {i}"}
            for i in range(5)
        ]
        embeddings = [[float(i) / 10.0] * EMBEDDING_DIM for i in range(5)]

        store.add_repo(
            repo_dict=repo,
            readme_text="",
            source_files=[],
            embeddings=embeddings,
            chunks=chunks,
        )

        query_vec = [0.0] * EMBEDDING_DIM
        results = store.search(query_vec, limit=2)
        assert len(results) == 2


class TestSerializeF32:
    def test_roundtrip(self):
        import struct
        vec = [1.0, 2.0, 3.0]
        data = _serialize_f32(vec)
        assert len(data) == 12  # 3 floats * 4 bytes
        unpacked = list(struct.unpack("3f", data))
        assert unpacked == vec
