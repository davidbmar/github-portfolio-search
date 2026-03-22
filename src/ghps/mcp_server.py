"""MCP server for GitHub Portfolio Search.

Implements the Model Context Protocol (MCP) over stdio using JSON-RPC 2.0.
Exposes portfolio search tools for Claude Code and Bob integration.

Uses the lightweight JSON-RPC approach (no mcp package dependency) so it
works with Python >=3.9.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
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
        "description": "Search the GitHub portfolio index by semantic similarity. Returns ranked results with repo name, score, snippet, and URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "portfolio_clusters",
        "description": "Return capability clusters of repos grouped by embedding similarity. Each cluster has a name and list of repo names.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "portfolio_repo_detail",
        "description": "Get full metadata for a specific repo including description, language, topics, stars, URL, README excerpt, and tech stack.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_name": {
                    "type": "string",
                    "description": "Name of the repository to look up",
                },
            },
            "required": ["repo_name"],
        },
    },
    {
        "name": "portfolio_reindex",
        "description": "Trigger re-indexing of a GitHub user's repositories. Returns the count of chunks indexed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "GitHub username whose repos should be re-indexed",
                },
            },
            "required": ["username"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _handle_portfolio_search(store: Any, embedder: Any, args: dict) -> List[dict]:
    """Execute portfolio_search tool."""
    query = args.get("query", "")
    top_k = args.get("top_k", 10)

    if not query:
        raise ValueError("query is required")

    query_vec = embedder.embed_text(query)
    raw = store.search(query_vec, limit=top_k * 3)

    db = store.connect()
    repo_urls: dict = {}
    for row in db.execute("SELECT name, url FROM repos").fetchall():
        repo_urls[row[0]] = row[1]

    best: Dict[str, dict] = {}
    for row in raw:
        repo_name = row["repo_name"]
        score = 1.0 - row["distance"]
        if repo_name not in best or score > best[repo_name]["score"]:
            best[repo_name] = {
                "repo_name": repo_name,
                "score": round(score, 4),
                "snippet": row["text"][:300],
                "url": repo_urls.get(repo_name, ""),
            }

    results = sorted(best.values(), key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def _handle_portfolio_clusters(store: Any, _args: dict) -> List[dict]:
    """Execute portfolio_clusters tool."""
    from ghps.clusters import ClusterEngine

    engine = ClusterEngine(store)
    cluster_list = engine.cluster_repos(n_clusters=10)

    return [
        {"name": c.name, "repos": c.repos, "size": len(c.repos)}
        for c in cluster_list
    ]


def _handle_portfolio_repo_detail(store: Any, args: dict) -> dict:
    """Execute portfolio_repo_detail tool."""
    repo_name = args.get("repo_name", "")
    if not repo_name:
        raise ValueError("repo_name is required")

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

    # Derive tech stack from file extensions in chunks
    source_rows = db.execute(
        "SELECT DISTINCT source FROM chunks WHERE repo_name = ? AND source != 'README'",
        (repo_name,),
    ).fetchall()
    tech_stack = list({Path(r[0]).suffix.lstrip(".") for r in source_rows if "." in r[0]})

    return {
        "name": repo_row[0],
        "description": repo_row[1],
        "language": repo_row[2],
        "topics": topics,
        "stars": repo_row[4],
        "updated_at": repo_row[5],
        "url": repo_row[6],
        "readme_excerpt": readme_excerpt[:2000],
        "tech_stack": tech_stack,
    }


def _handle_portfolio_reindex(store: Any, args: dict) -> dict:
    """Execute portfolio_reindex tool."""
    username = args.get("username", "")
    if not username:
        raise ValueError("username is required")

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

    return {"username": username, "chunks_indexed": total}


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
    store.connect()
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
