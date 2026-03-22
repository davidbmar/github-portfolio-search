"""Indexer that ties together github_client, embeddings, and store."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from .embeddings import EmbeddingPipeline
from .store import VectorStore

logger = logging.getLogger(__name__)

# Known technology keywords for topic inference from README content and repo names.
TOPIC_KEYWORDS: set[str] = {
    "voice", "aws", "s3", "lambda", "docker", "react", "python", "typescript",
    "llm", "rag", "whisper", "webrtc", "tts", "stt", "fastapi", "flask",
    "tensorflow", "pytorch", "kubernetes", "terraform", "cognito", "cloudfront",
    "sqs", "dynamodb", "api-gateway", "websocket", "grpc", "mcp", "telegram",
    "whatsapp", "fsm", "state-machine", "scheduler", "browser", "frontend",
    "backend", "cli", "streaming", "transcription", "diarization", "embeddings",
    "vector", "search", "semantic",
}


class Indexer:
    """Orchestrates fetching repos, generating embeddings, and storing them."""

    def __init__(
        self,
        store: VectorStore,
        pipeline: Optional[EmbeddingPipeline] = None,
    ) -> None:
        self.store = store
        self.pipeline = pipeline or EmbeddingPipeline()

    @staticmethod
    def extract_topics(repo_name: str, readme: str) -> list[str]:
        """Infer topic keywords from a repo name and README text.

        Scans for known technology keywords in:
        1. The README text (case-insensitive word boundary matching)
        2. The repo name (split on hyphens and underscores)

        Returns a sorted, deduplicated list of matched keywords.
        """
        found: set[str] = set()

        # Scan README text for keyword matches (word-boundary, case-insensitive)
        if readme:
            readme_lower = readme.lower()
            for kw in TOPIC_KEYWORDS:
                # Use word boundary matching so "class" doesn't match "classification"
                if re.search(r"(?:^|[\s\-_/,;:.(]){}(?:[\s\-_/,;:.)!?]|$)".format(re.escape(kw)), readme_lower):
                    found.add(kw)

        # Scan repo name tokens
        name_tokens = {t.lower() for t in re.split(r"[-_]", repo_name)}
        found.update(name_tokens & TOPIC_KEYWORDS)

        return sorted(found)

    def index_repos(self, repos: list[dict[str, Any]]) -> int:
        """Index a list of repo dicts into the vector store.

        Each repo dict should have keys: name, description, language, topics,
        stars, updated_at, url, readme (str), source_files (list of {path, content}).

        Returns the total number of chunks indexed.
        """
        total_chunks = 0

        for i, repo in enumerate(repos, 1):
            name = repo.get("name", "unknown")
            logger.info("Indexing repo %d/%d: %s", i, len(repos), name)

            readme = repo.get("readme", "")
            source_files = repo.get("source_files", [])

            # Build chunks from readme and source files
            chunks = self._build_chunks(name, readme, source_files)

            if not chunks:
                logger.warning("No content to index for repo %s", name)
                continue

            # Generate embeddings for all chunk texts
            texts = [c["text"] for c in chunks]
            embeddings = self.pipeline.embed_batch(texts)

            # Infer topics from README content and repo name
            inferred = self.extract_topics(name, readme)
            repo["inferred_topics"] = inferred

            # Merge GitHub topics with inferred topics (deduplicated)
            github_topics = repo.get("topics", [])
            merged = sorted(set(github_topics) | set(inferred))

            # Store everything
            repo_meta = {
                "name": name,
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "topics": merged,
                "stars": repo.get("stars", 0),
                "updated_at": repo.get("updated_at", ""),
                "url": repo.get("url", ""),
            }

            self.store.add_repo(
                repo_dict=repo_meta,
                readme_text=readme,
                source_files=source_files,
                embeddings=embeddings,
                chunks=chunks,
            )

            total_chunks += len(chunks)
            logger.info("Repo %s: %d chunks generated", name, len(chunks))

        logger.info("Indexing complete: %d repos, %d total chunks", len(repos), total_chunks)
        return total_chunks

    def _build_chunks(
        self, repo_name: str, readme: str, source_files: list[dict]
    ) -> list[dict]:
        """Build chunk dicts from readme and source files."""
        chunks: list[dict] = []

        # Chunk the README
        if readme and readme.strip():
            readme_chunks = self.pipeline.chunk_text(readme)
            for text in readme_chunks:
                chunks.append({"repo_name": repo_name, "source": "README", "text": text})

        # Chunk each source file
        for sf in source_files:
            path = sf.get("path", "unknown")
            content = sf.get("content", "")
            if not content or not content.strip():
                continue
            file_chunks = self.pipeline.chunk_text(content)
            for text in file_chunks:
                chunks.append({"repo_name": repo_name, "source": path, "text": text})

        return chunks

    def index_user(self, username: str, github_client: Any = None) -> int:
        """Fetch all repos for a user and index them.

        Fetches repo metadata, then enriches each repo with README content
        so there's actual text to embed and search.
        """
        if github_client is None:
            raise ValueError("github_client is required for index_user")

        logger.info("Fetching repos for user: %s", username)
        repos = github_client.fetch_repos(username)
        logger.info("Found %d repos for %s", len(repos), username)

        # Enrich each repo with README content
        for i, repo in enumerate(repos, 1):
            name = repo["name"]
            logger.info("Fetching README %d/%d: %s", i, len(repos), name)
            try:
                readme = github_client.fetch_readme(username, name)
                repo["readme"] = readme
            except Exception:
                logger.warning("Could not fetch README for %s", name)
                repo["readme"] = ""

        return self.index_repos(repos)
