"""Semantic search engine for GitHub portfolio repos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    indexed_at: str = ""
    freshness: str = ""


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
        raw = self.store.search(query_vec, limit=top_k * 3)

        # Look up repo metadata from the repos table
        repo_urls: dict[str, str] = {}
        repo_updated: dict[str, str] = {}
        repo_indexed: dict[str, str] = {}
        db = self.store.connect()
        for row in db.execute("SELECT name, url, updated_at, indexed_at FROM repos").fetchall():
            repo_urls[row[0]] = row[1]
            repo_updated[row[0]] = row[2] or ""
            repo_indexed[row[0]] = row[3] or ""

        # Deduplicate: keep only the best-scoring chunk per repo.
        # VectorStore returns distance (lower = more similar), convert to score.
        best_per_repo: dict[str, SearchResult] = {}
        for row in raw:
            repo_name = row["repo_name"]
            base_score = 1.0 - row["distance"]

            # Title boosting: 2x if any query term appears in repo name
            title_boost = _title_boost(query, repo_name)

            # Recency boosting: 1.2x (< 6 months), 1.0x (< 1 year), 0.8x (older)
            recency_boost = _recency_boost(repo_updated.get(repo_name, ""))

            score = base_score * title_boost * recency_boost

            if repo_name not in best_per_repo or score > best_per_repo[repo_name].score:
                idx_at = repo_indexed.get(repo_name, "")
                best_per_repo[repo_name] = SearchResult(
                    repo_name=repo_name,
                    chunk_text=row["text"],
                    score=score,
                    source=row["source"],
                    repo_url=repo_urls.get(repo_name, ""),
                    indexed_at=idx_at,
                    freshness=_freshness_label(idx_at),
                )

        results = sorted(best_per_repo.values(), key=lambda r: r.score, reverse=True)
        return results[:top_k]


def _title_boost(query: str, repo_name: str) -> float:
    """Return 2.0 if any query term appears in the repo name, else 1.0."""
    query_terms = query.lower().split()
    name_lower = repo_name.lower()
    for term in query_terms:
        if term in name_lower:
            return 2.0
    return 1.0


def _freshness_label(indexed_at: str) -> str:
    """Return a human-readable freshness label based on when the repo was indexed.

    - Indexed today: "today"
    - Indexed within the last 7 days: "this_week"
    - Indexed within the last 30 days: "this_month"
    - Older or unknown: "stale"
    """
    if not indexed_at:
        return "stale"
    try:
        indexed = datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_ago = (now - indexed).days
        if days_ago <= 0:
            return "today"
        elif days_ago <= 7:
            return "this_week"
        elif days_ago <= 30:
            return "this_month"
        else:
            return "stale"
    except (ValueError, TypeError):
        return "stale"


def _recency_boost(updated_at: str) -> float:
    """Return a boost factor based on how recently the repo was updated.

    - Updated within 6 months: 1.2x
    - Updated within 1 year: 1.0x
    - Older or unknown: 0.8x
    """
    if not updated_at:
        return 0.8
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_ago = (now - updated).days
        if days_ago <= 182:
            return 1.2
        elif days_ago <= 365:
            return 1.0
        else:
            return 0.8
    except (ValueError, TypeError):
        return 0.8
