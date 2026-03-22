"""Static JSON data export for the web UI."""

from __future__ import annotations

import json
import logging
import os
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ghps.store import VectorStore

logger = logging.getLogger(__name__)


def export_static_bundle(store: "VectorStore", output_dir: str) -> dict[str, str]:
    """Generate static JSON files for the web UI.

    Produces three files in *output_dir*:
      - repos.json     — all repos with metadata
      - clusters.json  — capability clusters with repo names
      - search-index.json — pre-computed search data for client-side search

    Returns a dict mapping filename to absolute path for each generated file.
    """
    os.makedirs(output_dir, exist_ok=True)

    paths: dict[str, str] = {}

    # --- repos.json ---
    repos_data = _build_repos(store)
    repos_path = os.path.join(output_dir, "repos.json")
    _write_json(repos_path, repos_data)
    paths["repos.json"] = repos_path
    logger.info("Exported %d repos to %s", len(repos_data), repos_path)

    # --- clusters.json ---
    clusters_data = _build_clusters(store)
    clusters_path = os.path.join(output_dir, "clusters.json")
    _write_json(clusters_path, clusters_data)
    paths["clusters.json"] = clusters_path
    logger.info("Exported %d clusters to %s", len(clusters_data), clusters_path)

    # --- search-index.json ---
    search_data = _build_search_index(store)
    search_path = os.path.join(output_dir, "search-index.json")
    _write_json(search_path, search_data)
    paths["search-index.json"] = search_path
    logger.info("Exported search index with %d entries to %s", len(search_data), search_path)

    return paths


def _build_repos(store: "VectorStore") -> list[dict]:
    """Build the repos list from the store."""
    db = store.connect()
    rows = db.execute(
        "SELECT name, description, language, topics, stars, updated_at, url FROM repos ORDER BY name"
    ).fetchall()

    repos = []
    for row in rows:
        topics_raw = row[3]
        try:
            topics = json.loads(topics_raw) if topics_raw else []
        except (json.JSONDecodeError, TypeError):
            topics = []

        repos.append({
            "name": row[0],
            "description": row[1] or "",
            "language": row[2] or "Unknown",
            "topics": topics,
            "stars": row[4],
            "updated_at": row[5] or "",
            "url": row[6] or "",
        })
    return repos


def _build_clusters(store: "VectorStore") -> list[dict]:
    """Build capability clusters using the ClusterEngine."""
    from ghps.clusters import ClusterEngine

    engine = ClusterEngine(store)
    try:
        clusters = engine.cluster_repos()
    except Exception:
        logger.warning("Clustering failed (possibly too few repos), returning empty list")
        return []

    return [
        {"name": c.name, "repos": c.repos}
        for c in clusters
    ]


def _build_search_index(store: "VectorStore") -> list[dict]:
    """Build a lightweight search index from chunk text.

    Each entry maps a repo to its searchable text tokens, enabling
    client-side full-text search without embeddings.
    """
    db = store.connect()
    rows = db.execute(
        "SELECT repo_name, source, text FROM chunks ORDER BY repo_name, id"
    ).fetchall()

    # Group chunks by repo
    repo_chunks: dict[str, list[dict]] = {}
    for row in rows:
        repo_name = row[0]
        repo_chunks.setdefault(repo_name, []).append({
            "source": row[1],
            "text": row[2],
        })

    # Also pull repo metadata for keyword boosting
    repo_rows = db.execute(
        "SELECT name, description, language, topics FROM repos"
    ).fetchall()
    repo_meta = {}
    for row in repo_rows:
        topics_raw = row[3]
        try:
            topics = json.loads(topics_raw) if topics_raw else []
        except (json.JSONDecodeError, TypeError):
            topics = []
        repo_meta[row[0]] = {
            "description": row[1] or "",
            "language": row[2] or "",
            "topics": topics,
        }

    entries = []
    for repo_name, chunks in sorted(repo_chunks.items()):
        meta = repo_meta.get(repo_name, {})
        # Combine all text into searchable tokens
        all_text = " ".join(c["text"] for c in chunks)
        keywords = _extract_keywords(all_text)

        # Boost with metadata
        if meta.get("description"):
            keywords.extend(_extract_keywords(meta["description"]))
        if meta.get("language"):
            keywords.append(meta["language"].lower())
        for topic in meta.get("topics", []):
            keywords.append(topic.lower())

        # Deduplicate and sort
        unique_keywords = sorted(set(keywords))

        entries.append({
            "repo": repo_name,
            "keywords": unique_keywords,
            "chunks": [{"source": c["source"], "text": c["text"][:200]} for c in chunks],
        })

    return entries


def _extract_keywords(text: str) -> list[str]:
    """Extract lowercase keywords from text, filtering short/stop words."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
        "this", "that", "not", "has", "had", "have", "will", "can", "do",
    }
    words = text.lower().split()
    return [
        w.strip(".,;:!?()[]{}\"'`")
        for w in words
        if len(w) > 2 and w.lower().strip(".,;:!?()[]{}\"'`") not in stop_words
    ]


def _write_json(path: str, data: object) -> None:
    """Write data as formatted JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
