"""Semantic search engine for GitHub portfolio repos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ghps.embeddings import EmbeddingPipeline
    from ghps.store import VectorStore


@dataclass
class SearchResult:
    """A single search result returned by the engine."""

    repo_name: str
    chunk_text: str
    score: float
    source: str
    repo_url: str


class SearchEngine:
    """Wraps VectorStore + EmbeddingPipeline to provide semantic search."""

    def __init__(self, store: "VectorStore", embedder: "EmbeddingPipeline") -> None:
        self.store = store
        self.embedder = embedder

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Search indexed repos by semantic similarity.

        Args:
            query: Natural-language search query.
            top_k: Maximum number of results to return.

        Returns:
            List of SearchResult sorted by cosine similarity descending,
            deduplicated so only the best chunk per repo is kept.
        """
        query_vec = self.embedder.embed_text(query)

        # Fetch more candidates than top_k so we still have enough
        # after deduplication.
        raw = self.store.search(query_vec, top_k=top_k * 3)

        # Deduplicate: keep only the best-scoring chunk per repo.
        best_per_repo: dict[str, SearchResult] = {}
        for row in raw:
            repo_name = row["repo_name"]
            score = row["score"]
            if repo_name not in best_per_repo or score > best_per_repo[repo_name].score:
                best_per_repo[repo_name] = SearchResult(
                    repo_name=repo_name,
                    chunk_text=row["text"],
                    score=score,
                    source=row["source"],
                    repo_url=row["url"],
                )

        results = sorted(best_per_repo.values(), key=lambda r: r.score, reverse=True)
        return results[:top_k]
