"""Indexer that ties together github_client, embeddings, and store."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
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

    def index_repos(
        self, repos: list[dict[str, Any]], *, dry_run: bool = False
    ) -> int:
        """Index a list of repo dicts into the vector store.

        Each repo dict should have keys: name, description, language, topics,
        stars, updated_at, url, readme (str), source_files (list of {path, content}).

        Args:
            repos: List of repo metadata dicts.
            dry_run: If True, show what would be indexed without making changes.

        Returns the total number of chunks indexed (or that would be indexed).
        """
        total_chunks = 0
        indexed_count = 0
        failed_count = 0
        skipped_count = 0
        now = datetime.now(timezone.utc).isoformat()

        for i, repo in enumerate(repos, 1):
            name = repo.get("name", "unknown")
            logger.info("Indexing repo %d/%d: %s", i, len(repos), name)

            try:
                readme = repo.get("readme", "")
                source_files = repo.get("source_files", [])

                # Build chunks from readme and source files
                chunks = self._build_chunks(name, readme, source_files)

                if not chunks:
                    logger.warning("No content to index for repo %s", name)
                    skipped_count += 1
                    continue

                if dry_run:
                    logger.info(
                        "[dry-run] Would index %s: %d chunks", name, len(chunks)
                    )
                    total_chunks += len(chunks)
                    indexed_count += 1
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
                    "url": repo.get("html_url", "") or repo.get("url", ""),
                    "private": repo.get("private", False),
                    "indexed_at": now,
                    "portfolio": repo.get("portfolio", ""),
                }

                self.store.add_repo(
                    repo_dict=repo_meta,
                    readme_text=readme,
                    source_files=source_files,
                    embeddings=embeddings,
                    chunks=chunks,
                )

                total_chunks += len(chunks)
                indexed_count += 1
                logger.info("Repo %s: %d chunks generated", name, len(chunks))

            except Exception:
                failed_count += 1
                logger.warning("Failed to index repo %s, skipping", name, exc_info=True)

        prefix = "[dry-run] " if dry_run else ""
        logger.info(
            "%sIndexing complete: %d repos indexed, %d failed, %d skipped, %d total chunks",
            prefix,
            indexed_count,
            failed_count,
            skipped_count,
            total_chunks,
        )
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

    def index_user(
        self, username: str, github_client: Any = None, *, dry_run: bool = False
    ) -> int:
        """Fetch all repos for a user and index them.

        Fetches repo metadata, then enriches each repo with README content
        so there's actual text to embed and search.
        """
        if github_client is None:
            raise ValueError("github_client is required for index_user")

        logger.info("Fetching repos for user: %s", username)
        repos = github_client.fetch_repos(username)
        logger.info("Found %d repos for %s", len(repos), username)

        # Enrich each repo with README content and portfolio.json
        for i, repo in enumerate(repos, 1):
            name = repo["name"]
            logger.info("Fetching README %d/%d: %s", i, len(repos), name)
            try:
                readme = github_client.fetch_readme(username, name)
                repo["readme"] = readme
            except Exception:
                logger.warning("Could not fetch README for %s", name)
                repo["readme"] = ""

            try:
                portfolio_data = github_client.fetch_portfolio_json(username, name)
                if portfolio_data is not None:
                    repo["portfolio"] = json.dumps(portfolio_data)
                    logger.info("Found portfolio.json for %s", name)
                else:
                    repo["portfolio"] = ""
            except Exception:
                logger.warning("Could not fetch portfolio.json for %s", name)
                repo["portfolio"] = ""

        return self.index_repos(repos, dry_run=dry_run)
