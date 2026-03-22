"""SQLite-vec vector store for repo embeddings."""

from __future__ import annotations

import json
import logging
import struct
from typing import Optional

try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3

import sqlite_vec

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384


def _serialize_f32(vec: list[float]) -> bytes:
    """Serialize a float vector to bytes for sqlite-vec."""
    return struct.pack(f"{len(vec)}f", *vec)


class VectorStore:
    """SQLite-vec backed vector store for repository embeddings."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self.db: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self.db is None:
            self.db = sqlite3.connect(self.db_path)
            self.db.enable_load_extension(True)
            sqlite_vec.load(self.db)
            self.db.enable_load_extension(False)
            self.db.row_factory = sqlite3.Row
        return self.db

    def create_index(self) -> None:
        """Create the database schema: repos, chunks, repo_files tables."""
        db = self.connect()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS repos (
                name TEXT PRIMARY KEY,
                description TEXT,
                language TEXT,
                topics TEXT,
                stars INTEGER DEFAULT 0,
                updated_at TEXT,
                url TEXT
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_name TEXT NOT NULL,
                source TEXT NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY (repo_name) REFERENCES repos(name)
            );

            CREATE TABLE IF NOT EXISTS repo_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_name TEXT NOT NULL,
                path TEXT NOT NULL,
                content TEXT,
                FOREIGN KEY (repo_name) REFERENCES repos(name)
            );
        """)

        # Create the sqlite-vec virtual table for vector search
        db.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(embedding float[{EMBEDDING_DIM}])"
        )
        db.commit()

    def add_repo(
        self,
        repo_dict: dict,
        readme_text: str,
        source_files: list[dict],
        embeddings: list[list[float]],
        chunks: list[dict],
    ) -> None:
        """Index a repo with its metadata, files, chunks, and embeddings.

        Args:
            repo_dict: Repo metadata with keys: name, description, language, topics, stars, updated_at, url
            readme_text: Full README content
            source_files: List of dicts with keys: path, content
            embeddings: Pre-computed embeddings for each chunk
            chunks: List of dicts with keys: repo_name, source, text
        """
        db = self.connect()

        topics_json = json.dumps(repo_dict.get("topics", []))
        db.execute(
            """INSERT OR REPLACE INTO repos (name, description, language, topics, stars, updated_at, url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                repo_dict["name"],
                repo_dict.get("description", ""),
                repo_dict.get("language", ""),
                topics_json,
                repo_dict.get("stars", 0),
                repo_dict.get("updated_at", ""),
                repo_dict.get("url", ""),
            ),
        )

        # Store source files
        for sf in source_files:
            db.execute(
                "INSERT INTO repo_files (repo_name, path, content) VALUES (?, ?, ?)",
                (repo_dict["name"], sf["path"], sf.get("content", "")),
            )

        # Store chunks and their embeddings
        for chunk, embedding in zip(chunks, embeddings):
            cursor = db.execute(
                "INSERT INTO chunks (repo_name, source, text) VALUES (?, ?, ?)",
                (chunk["repo_name"], chunk["source"], chunk["text"]),
            )
            chunk_id = cursor.lastrowid
            db.execute(
                "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
                (chunk_id, _serialize_f32(embedding)),
            )

        db.commit()
        logger.info("Indexed repo %s with %d chunks", repo_dict["name"], len(chunks))

    def search(self, query_embedding: list[float], limit: int = 10) -> list[dict]:
        """Search for similar chunks by vector similarity.

        Returns list of dicts with keys: chunk_id, repo_name, source, text, distance
        """
        db = self.connect()
        rows = db.execute(
            """
            SELECT v.rowid, v.distance, c.repo_name, c.source, c.text
            FROM vec_chunks v
            JOIN chunks c ON c.id = v.rowid
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY v.distance
            """,
            (_serialize_f32(query_embedding), limit),
        ).fetchall()

        return [
            {
                "chunk_id": row[0],
                "distance": row[1],
                "repo_name": row[2],
                "source": row[3],
                "text": row[4],
            }
            for row in rows
        ]

    def close(self) -> None:
        if self.db is not None:
            self.db.close()
            self.db = None
