"""MCP server for GitHub Portfolio Search.

Implements the Model Context Protocol (MCP) over stdio using JSON-RPC 2.0.
Exposes portfolio search tools for Claude Code and AI agent integration.

Uses a lightweight JSON-RPC approach so it works with Python >=3.9 without
requiring the mcp SDK (which needs Python >=3.10).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions (JSON Schema for MCP tool listing)
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "portfolio_search",
        "description": (
            "Search David's GitHub portfolio by semantic similarity. "
            "Returns ranked results with repo name, description, score, language, and topics."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query (e.g. 'presigned URL', 'voice transcription')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "portfolio_clusters",
        "description": (
            "Return capability clusters of repos grouped by embedding similarity. "
            "Each cluster has a name, repo count, and list of repo names."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "portfolio_repo_detail",
        "description": (
            "Get full metadata for a specific repo including description, language, "
            "topics, stars, updated_at, html_url, and cluster assignment."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the repository to look up",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "portfolio_reindex",
        "description": "Trigger re-indexing of GitHub repositories. Returns a status message.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

_NO_INDEX_MSG = (
    "No portfolio index found. Run 'ghps index --user <username>' to build "
    "the search index first, or use portfolio_reindex() to trigger indexing."
)


def _check_index(store: Any) -> None:
    """Raise ValueError if the store has no indexed repos."""
    db = store.connect()
    try:
        count = db.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
    except Exception:
        raise ValueError(_NO_INDEX_MSG)
    if count == 0:
        raise ValueError(_NO_INDEX_MSG)


def _handle_portfolio_search(store: Any, embedder: Any, args: dict) -> List[dict]:
    """Execute portfolio_search tool."""
    query = args.get("query", "")
    limit = args.get("limit", args.get("top_k", 10))

    if not query:
        raise ValueError("query is required")

    _check_index(store)

    query_vec = embedder.embed_text(query)
    raw = store.search(query_vec, limit=limit * 3)

    db = store.connect()
    repo_meta: Dict[str, dict] = {}
    for row in db.execute(
        "SELECT name, description, language, topics, url FROM repos"
    ).fetchall():
        topics = []
        try:
            topics = json.loads(row[3]) if row[3] else []
        except (json.JSONDecodeError, TypeError):
            pass
        repo_meta[row[0]] = {
            "description": row[1] or "",
            "language": row[2] or "",
            "topics": topics,
            "url": row[4] or "",
        }

    best: Dict[str, dict] = {}
    for row in raw:
        repo_name = row["repo_name"]
        score = 1.0 - row["distance"]
        if repo_name not in best or score > best[repo_name]["score"]:
            meta = repo_meta.get(repo_name, {})
            best[repo_name] = {
                "name": repo_name,
                "repo_name": repo_name,
                "description": meta.get("description", ""),
                "score": round(score, 4),
                "language": meta.get("language", ""),
                "topics": meta.get("topics", []),
                "snippet": row["text"][:300],
                "url": meta.get("url", ""),
            }

    results = sorted(best.values(), key=lambda x: x["score"], reverse=True)
    return results[:limit]


def _handle_portfolio_clusters(store: Any, _args: dict) -> List[dict]:
    """Execute portfolio_clusters tool."""
    _check_index(store)

    from ghps.clusters import ClusterEngine

    engine = ClusterEngine(store)
    cluster_list = engine.cluster_repos(n_clusters=6)

    return [
        {"name": c.name, "repos": c.repos, "size": len(c.repos)}
        for c in cluster_list
    ]


def _handle_portfolio_repo_detail(store: Any, args: dict) -> dict:
    """Execute portfolio_repo_detail tool."""
    repo_name = args.get("name", args.get("repo_name", ""))
    if not repo_name:
        raise ValueError("repo_name is required")

    _check_index(store)

    db = store.connect()
    repo_row = db.execute(
        "SELECT name, description, language, topics, stars, updated_at, url FROM repos WHERE name = ?",
        (repo_name,),
    ).fetchone()

    if not repo_row:
        raise ValueError(f"Repo '{repo_name}' not found")

    topics: list = []
    try:
        topics = json.loads(repo_row[3]) if repo_row[3] else []
    except (json.JSONDecodeError, TypeError):
        pass

    readme_chunks = db.execute(
        "SELECT text FROM chunks WHERE repo_name = ? AND source LIKE '%README%' ORDER BY id LIMIT 3",
        (repo_name,),
    ).fetchall()
    readme_excerpt = "\n\n".join(r[0] for r in readme_chunks) if readme_chunks else ""

    source_rows = db.execute(
        "SELECT DISTINCT source FROM chunks WHERE repo_name = ? AND source != 'README'",
        (repo_name,),
    ).fetchall()
    tech_stack = list({Path(r[0]).suffix.lstrip(".") for r in source_rows if "." in r[0]})

    # Determine cluster assignment
    cluster = ""
    try:
        from ghps.clusters import ClusterEngine
        engine = ClusterEngine(store)
        clusters = engine.cluster_repos(n_clusters=6)
        for c in clusters:
            if repo_name in c.repos:
                cluster = c.name
                break
    except Exception:
        pass

    return {
        "name": repo_row[0],
        "description": repo_row[1] or "",
        "language": repo_row[2] or "",
        "topics": topics,
        "stars": repo_row[4] or 0,
        "updated_at": repo_row[5] or "",
        "html_url": repo_row[6] or "",
        "url": repo_row[6] or "",
        "readme_excerpt": readme_excerpt[:2000],
        "tech_stack": tech_stack,
        "cluster": cluster,
    }


def _handle_portfolio_reindex(store: Any, args: dict) -> dict:
    """Execute portfolio_reindex tool."""
    username = args.get("username", "davidbmar")

    from ghps import github_client
    from ghps.embeddings import EmbeddingPipeline
    from ghps.indexer import Indexer

    raw_repos = github_client.fetch_repos(username)
    repos = []
    for r in raw_repos:
        readme = github_client.fetch_readme(username, r["name"])
        files = github_client.fetch_top_files(username, r["name"])
        repos.append({
            "name": r["name"],
            "description": r.get("description", ""),
            "language": r.get("language", ""),
            "topics": r.get("topics", []),
            "stars": r.get("stars", 0),
            "updated_at": r.get("updated_at", ""),
            "url": r.get("html_url", ""),
            "readme": readme,
            "source_files": [{"path": p, "content": c} for p, c in files],
        })

    pipeline = EmbeddingPipeline()
    indexer = Indexer(store=store, pipeline=pipeline)
    total = indexer.index_repos(repos)

    return {
        "status": f"Reindex complete: {total} chunks indexed for {username}",
        "username": username,
        "chunks_indexed": total,
    }


# ---------------------------------------------------------------------------
# JSON-RPC / MCP protocol handling
# ---------------------------------------------------------------------------


def _jsonrpc_response(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _jsonrpc_error(id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def handle_message(msg: dict, store: Any, embedder: Any) -> Optional[dict]:
    """Process a single JSON-RPC message and return a response (or None for notifications)."""
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":
        return _jsonrpc_response(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "ghps-mcp",
                "version": "0.1.0",
            },
        })

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return _jsonrpc_response(msg_id, {"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "portfolio_search":
                result = _handle_portfolio_search(store, embedder, arguments)
            elif tool_name == "portfolio_clusters":
                result = _handle_portfolio_clusters(store, arguments)
            elif tool_name == "portfolio_repo_detail":
                result = _handle_portfolio_repo_detail(store, arguments)
            elif tool_name == "portfolio_reindex":
                result = _handle_portfolio_reindex(store, arguments)
            else:
                return _jsonrpc_error(msg_id, -32601, f"Unknown tool: {tool_name}")

            return _jsonrpc_response(msg_id, {
                "content": [{"type": "text", "text": json.dumps(result)}],
            })
        except Exception as exc:
            return _jsonrpc_response(msg_id, {
                "content": [{"type": "text", "text": json.dumps({"error": str(exc)})}],
                "isError": True,
            })

    if method == "ping":
        return _jsonrpc_response(msg_id, {})

    # Unknown method
    if msg_id is not None:
        return _jsonrpc_error(msg_id, -32601, f"Method not found: {method}")
    return None


def _read_message(stream) -> Optional[dict]:
    """Read a JSON-RPC message from a stream using MCP stdio framing (newline-delimited JSON)."""
    line = stream.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    return json.loads(line)


def _write_message(msg: dict, stream) -> None:
    """Write a JSON-RPC message to a stream."""
    data = json.dumps(msg)
    stream.write(data + "\n")
    stream.flush()


def run_stdio(db_path: str) -> None:
    """Run the MCP server over stdio (newline-delimited JSON-RPC)."""
    from ghps.embeddings import EmbeddingPipeline
    from ghps.store import VectorStore

    store = VectorStore(db_path)
    try:
        store.connect()
    except Exception as exc:
        logger.error("Failed to connect to database: %s", exc)
        logger.info("The server will start but tools will return index-not-found errors.")

    embedder = EmbeddingPipeline()

    logger.info("ghps-mcp server started — db=%s", db_path)

    try:
        while True:
            msg = _read_message(sys.stdin)
            if msg is None:
                break

            response = handle_message(msg, store, embedder)
            if response is not None:
                _write_message(response, sys.stdout)
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        store.close()
        logger.info("ghps-mcp server stopped")


def main() -> None:
    """Entry point for ghps-mcp console script."""
    parser = argparse.ArgumentParser(description="GitHub Portfolio Search MCP server")
    parser.add_argument(
        "--db",
        type=str,
        default=os.path.expanduser("~/.ghps/index.db"),
        help="Path to SQLite database (default: ~/.ghps/index.db)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    run_stdio(args.db)


if __name__ == "__main__":
    main()
