"""Cluster repos by embedding similarity using KMeans."""

from __future__ import annotations

import json
import logging
import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from sklearn.cluster import KMeans

if TYPE_CHECKING:
    from ghps.store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class Cluster:
    """A group of semantically similar repos."""

    name: str
    repos: list[str] = field(default_factory=list)
    centroid: list[float] = field(default_factory=list)


class ClusterEngine:
    """Groups repos by embedding similarity using KMeans."""

    def __init__(self, store: "VectorStore") -> None:
        self.store = store

    def cluster_repos(self, n_clusters: int = 10) -> list[Cluster]:
        """Group repos into clusters based on their average embedding.

        Each repo's embedding is the mean of its chunk embeddings.
        Returns a list of Cluster objects with name, repos, and centroid.
        """
        db = self.store.connect()

        # Get all repos
        repos = db.execute("SELECT name, description, language, topics FROM repos").fetchall()
        if not repos:
            return []

        repo_names = [r[0] for r in repos]
        repo_meta = {r[0]: {"description": r[1], "language": r[2], "topics": r[3]} for r in repos}

        # Compute average embedding per repo from its chunks
        dim = 384  # EMBEDDING_DIM
        repo_embeddings: dict[str, np.ndarray] = {}
        for name in repo_names:
            rows = db.execute(
                """
                SELECT v.embedding FROM vec_chunks v
                JOIN chunks c ON c.id = v.rowid
                WHERE c.repo_name = ?
                """,
                (name,),
            ).fetchall()
            if rows:
                vecs = [np.array(struct.unpack(f"{dim}f", r[0])) for r in rows]
                repo_embeddings[name] = np.mean(vecs, axis=0)

        if not repo_embeddings:
            return []

        # Build matrix of repo embeddings
        names = list(repo_embeddings.keys())
        matrix = np.array([repo_embeddings[n] for n in names])

        # Adjust n_clusters if we have fewer repos
        k = min(n_clusters, len(names))
        if k < 1:
            return []

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(matrix)

        # Build clusters
        clusters_map: dict[int, list[str]] = {}
        for name, label in zip(names, labels):
            clusters_map.setdefault(int(label), []).append(name)

        result: list[Cluster] = []
        for label_id, cluster_repos in sorted(clusters_map.items()):
            centroid = kmeans.cluster_centers_[label_id].tolist()
            name = _generate_cluster_name(cluster_repos, repo_meta)
            result.append(Cluster(name=name, repos=cluster_repos, centroid=centroid))

        return result


def _generate_cluster_name(repo_names: list[str], repo_meta: dict) -> str:
    """Generate a human-readable cluster name from repo metadata."""
    languages: dict[str, int] = {}
    topics: dict[str, int] = {}

    for name in repo_names:
        meta = repo_meta.get(name, {})
        lang = meta.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        raw_topics = meta.get("topics", "[]")
        try:
            topic_list = json.loads(raw_topics) if isinstance(raw_topics, str) else (raw_topics or [])
        except (json.JSONDecodeError, TypeError):
            topic_list = []
        for t in topic_list:
            topics[t] = topics.get(t, 0) + 1

    parts: list[str] = []
    if languages:
        top_lang = max(languages, key=languages.get)  # type: ignore[arg-type]
        parts.append(top_lang)
    if topics:
        top_topic = max(topics, key=topics.get)  # type: ignore[arg-type]
        parts.append(top_topic)

    if parts:
        return " / ".join(parts)
    return f"cluster-{repo_names[0]}" if repo_names else "unknown"
