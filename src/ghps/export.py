"""Static JSON data export for the web UI."""

from __future__ import annotations

import json
import logging
import os
import struct
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
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

    # --- similarity.json ---
    similarity_data = _build_similarity(store)
    similarity_path = os.path.join(output_dir, "similarity.json")
    _write_json(similarity_path, similarity_data)
    paths["similarity.json"] = similarity_path
    logger.info("Exported similarity data for %d repos to %s", len(similarity_data), similarity_path)

    # --- suggestions.json ---
    suggestions_data = _build_suggestions(store)
    suggestions_path = os.path.join(output_dir, "suggestions.json")
    _write_json(suggestions_path, suggestions_data)
    paths["suggestions.json"] = suggestions_path
    logger.info("Exported suggestions to %s", suggestions_path)

    return paths


def _build_repos(store: "VectorStore") -> list[dict]:
    """Build the repos list from the store, sorted by relevance score."""
    from ghps.search import _recency_boost

    db = store.connect()

    # Pre-fetch first README chunk per repo for excerpts
    readme_rows = db.execute(
        "SELECT repo_name, text FROM chunks WHERE source = 'README' "
        "GROUP BY repo_name HAVING MIN(id)"
    ).fetchall()
    readme_map = {row[0]: row[1][:300] for row in readme_rows}

    # Pre-fetch private flag (column may not exist in older DBs)
    private_map: dict[str, bool] = {}
    try:
        priv_rows = db.execute("SELECT name, private FROM repos WHERE private = 1").fetchall()
        for pr in priv_rows:
            private_map[pr[0]] = True
    except Exception:
        pass

    # Pre-fetch portfolio data (column may not exist in older DBs)
    portfolio_map: dict[str, dict] = {}
    try:
        port_rows = db.execute("SELECT name, portfolio FROM repos WHERE portfolio IS NOT NULL AND portfolio != ''").fetchall()
        for pr in port_rows:
            try:
                portfolio_map[pr[0]] = json.loads(pr[1])
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception:
        pass

    # Try to read inferred_topics if agentA has added the column
    try:
        rows = db.execute(
            "SELECT name, description, language, topics, stars, updated_at, url, inferred_topics FROM repos"
        ).fetchall()
        has_inferred = True
    except Exception:
        rows = db.execute(
            "SELECT name, description, language, topics, stars, updated_at, url FROM repos"
        ).fetchall()
        has_inferred = False

    last_indexed = datetime.now(timezone.utc).isoformat()

    repos = []
    for row in rows:
        topics_raw = row[3]
        try:
            topics = json.loads(topics_raw) if topics_raw else []
        except (json.JSONDecodeError, TypeError):
            topics = []

        # Merge inferred topics if available
        if has_inferred:
            inferred_raw = row[7]
            try:
                inferred = json.loads(inferred_raw) if inferred_raw else []
            except (json.JSONDecodeError, TypeError):
                inferred = []
            topics = list(dict.fromkeys(topics + inferred))

        stars = row[4] or 0
        updated_at = row[5] or ""
        recency = _recency_boost(updated_at)
        relevance_score = stars + recency

        description = row[1] or ""
        readme_excerpt = readme_map.get(row[0], "")

        # Auto-generate description from README if GitHub description is empty
        if not description and readme_excerpt:
            description = _description_from_readme(readme_excerpt, row[0])

        repo_entry = {
            "name": row[0],
            "description": description,
            "language": row[2] or "Unknown",
            "topics": topics,
            "stars": stars,
            "updated_at": updated_at,
            "url": row[6] or "",
            "private": private_map.get(row[0], False),
            "last_indexed": last_indexed,
            "relevance_score": relevance_score,
            "readme_excerpt": readme_excerpt,
        }

        portfolio = portfolio_map.get(row[0])
        if portfolio:
            repo_entry["showcase"] = bool(portfolio.get("showcase", False))
            repo_entry["liveUrl"] = portfolio.get("liveUrl", "")
            repo_entry["role"] = portfolio.get("role", "")
            repo_entry["builtWith"] = portfolio.get("builtWith", [])
            repo_entry["relatedProjects"] = portfolio.get("relatedProjects", [])
            repo_entry["highlight"] = portfolio.get("highlight", "")
            repo_entry["category"] = portfolio.get("category", "")

        repos.append(repo_entry)

    # Sort by relevance score descending (stars + recency)
    repos.sort(key=lambda r: r["relevance_score"], reverse=True)
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


def _build_similarity(store: "VectorStore") -> dict[str, list[dict]]:
    """Compute pairwise cosine similarity between repos using average embeddings.

    For each repo, returns the top-8 most similar repos with scores.
    """
    import numpy as np
    from ghps.store import EMBEDDING_DIM

    db = store.connect()

    # Get all chunk embeddings grouped by repo
    rows = db.execute(
        "SELECT c.repo_name, v.embedding FROM chunks c "
        "JOIN vec_chunks v ON v.rowid = c.id "
        "ORDER BY c.repo_name"
    ).fetchall()

    # Group embeddings by repo name
    repo_embeddings: dict[str, list[list[float]]] = {}
    for row in rows:
        repo_name = row[0]
        raw = row[1]
        vec = list(struct.unpack(f"{EMBEDDING_DIM}f", raw))
        repo_embeddings.setdefault(repo_name, []).append(vec)

    if not repo_embeddings:
        return {}

    # Compute average embedding per repo
    repo_names = sorted(repo_embeddings.keys())
    avg_vectors = []
    for name in repo_names:
        vecs = np.array(repo_embeddings[name])
        avg_vectors.append(vecs.mean(axis=0))

    matrix = np.array(avg_vectors)

    # Cosine similarity: normalize then dot product
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)  # avoid division by zero
    normalized = matrix / norms
    sim_matrix = normalized @ normalized.T

    # Build result: top-8 similar repos per repo (excluding self)
    result = {}
    for i, name in enumerate(repo_names):
        scores = []
        for j, other_name in enumerate(repo_names):
            if i != j:
                scores.append({"name": other_name, "score": round(float(sim_matrix[i, j]), 4)})
        scores.sort(key=lambda x: x["score"], reverse=True)
        result[name] = scores[:8]

    return result


def _build_suggestions(store: "VectorStore") -> dict[str, list]:
    """Build autocomplete suggestions from repo names, topics, and popular queries."""
    db = store.connect()

    # Collect repo names
    repo_rows = db.execute("SELECT name FROM repos ORDER BY name").fetchall()
    repos = [row[0] for row in repo_rows]

    # Collect unique topics
    topic_rows = db.execute("SELECT topics FROM repos WHERE topics IS NOT NULL").fetchall()
    all_topics: set[str] = set()
    for row in topic_rows:
        try:
            topics = json.loads(row[0]) if row[0] else []
        except (json.JSONDecodeError, TypeError):
            topics = []
        all_topics.update(topics)

    # Try to read popular queries from analytics DB
    queries: list[str] = []
    try:
        analytics_db_path = os.path.join(Path.home(), ".ghps", "analytics.db")
        if os.path.exists(analytics_db_path):
            from ghps.analytics import get_popular_queries
            popular = get_popular_queries(limit=20, db_path=analytics_db_path)
            queries = [p["query"] for p in popular]
    except Exception:
        logger.debug("Could not read analytics DB for suggestions, using empty queries")

    return {
        "repos": repos,
        "topics": sorted(all_topics),
        "queries": queries,
    }


def _description_from_readme(readme_text: str, repo_name: str) -> str:
    """Extract a description from README text when GitHub description is empty.

    Strips the markdown heading (# repo-name), takes the first meaningful
    sentence or ~150 chars as the description.
    """
    import re

    lines = readme_text.strip().splitlines()
    useful = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip markdown headings that are just the repo name
        if stripped.startswith("#"):
            heading = re.sub(r"^#+\s*", "", stripped)
            # If heading is just the repo name (with optional punctuation/dashes), skip it
            name_clean = repo_name.lower().replace("-", " ").replace("_", " ")
            heading_clean = heading.lower().replace("-", " ").replace("_", " ").strip(" —–-:")
            if heading_clean == name_clean:
                continue
            # If heading starts with repo name + separator, strip the name part
            if heading_clean.startswith(name_clean):
                remainder = heading[len(repo_name):].lstrip(" —–-:")
                if remainder:
                    useful.append(remainder.strip())
                    continue
            # Otherwise use the heading text (without #)
            useful.append(heading)
            continue
        # Skip badges, images, links-only lines
        if stripped.startswith("![") or stripped.startswith("[![") or stripped.startswith("<img"):
            continue
        useful.append(stripped)
        # Stop after we have enough text
        if sum(len(u) for u in useful) > 200:
            break

    if not useful:
        return ""

    text = " ".join(useful)
    # Clean up markdown artifacts
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*([^*]+)\*", r"\1", text)  # italic
    text = re.sub(r"`([^`]+)`", r"\1", text)  # inline code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate to ~150 chars at a word boundary
    if len(text) > 150:
        text = text[:150].rsplit(" ", 1)[0] + "..."

    return text


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
