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

    def cluster_repos(self, n_clusters: int = 6) -> list[Cluster]:
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

        # Generate unique names
        used_names: set[str] = set()
        result: list[Cluster] = []
        for label_id, cluster_repos in sorted(clusters_map.items()):
            centroid = kmeans.cluster_centers_[label_id].tolist()
            name = _generate_cluster_name(cluster_repos, repo_meta, used_names)
            used_names.add(name)
            result.append(Cluster(name=name, repos=cluster_repos, centroid=centroid))

        return result


# Keywords to scan for in repo names + descriptions → capability labels
_KEYWORD_CAPABILITIES: list[tuple[list[str], str]] = [
    (["voice", "speech", "tts", "stt", "piper", "whisper", "diarization"], "Voice & Speech Processing"),
    (["transcri", "asr", "speech-to-text", "whisper"], "Transcription & ASR"),
    (["browser", "webrtc", "webassembly", "wasm", "frontend", "webgpu"], "Browser & Frontend"),
    (["s3", "lambda", "cloudfront", "aws", "presigned", "api-gateway", "sqs", "cloudformation"], "AWS Infrastructure"),
    (["llm", "rag", "vector", "embedding", "search", "semantic", "ai", "gpt", "claude", "chatbot"], "AI & Search"),
    (["docker", "deploy", "ci", "cd", "terraform", "k8s", "kubernetes"], "Infrastructure & DevOps"),
    (["mcp", "cli", "tool", "telegram", "whatsapp", "bot"], "Developer Tools & Bots"),
    (["fsm", "state-machine", "scheduler", "workflow", "calendar"], "Workflow & Automation"),
    (["video", "audio", "stream", "media", "youtube", "commercial"], "Media Processing"),
]


def _generate_cluster_name(
    repo_names: list[str], repo_meta: dict, used_names: set[str]
) -> str:
    """Generate a capability name by scanning repo names and descriptions for keywords."""
    capability_votes: dict[str, int] = {}

    for name in repo_names:
        meta = repo_meta.get(name, {})
        desc = (meta.get("description") or "").lower()
        searchable = f"{name.lower()} {desc}"

        for keywords, capability in _KEYWORD_CAPABILITIES:
            for kw in keywords:
                if kw in searchable:
                    capability_votes[capability] = capability_votes.get(capability, 0) + 1
                    break  # one vote per capability per repo

    # Pick the highest-voted capability that hasn't been used
    if capability_votes:
        for cap, _ in sorted(capability_votes.items(), key=lambda x: -x[1]):
            if cap not in used_names:
                return cap

    # Fallback: find the most common meaningful word in descriptions
    words: dict[str, int] = {}
    stop = {
        "the", "a", "an", "and", "or", "for", "to", "of", "with", "in", "on",
        "is", "it", "this", "that", "from", "using", "based", "simple", "basic",
        "new", "test", "repo", "project", "file", "files", "code", "app",
    }
    for name in repo_names:
        meta = repo_meta.get(name, {})
        desc = (meta.get("description") or "").lower()
        for w in desc.split():
            w = w.strip(".,;:!?()-/\"'")
            if len(w) > 3 and w not in stop:
                words[w] = words.get(w, 0) + 1

    if words:
        top_words = sorted(words, key=words.get, reverse=True)[:2]  # type: ignore[arg-type]
        candidate = " & ".join(w.title() for w in top_words)
        if candidate not in used_names:
            return candidate

    return f"Other Projects ({len(repo_names)} repos)"
