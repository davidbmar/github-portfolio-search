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
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions (JSON Schema for MCP tool listing)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
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
    {
        "name": "portfolio_find_docs",
        "description": (
            "Search the AI-generated project docs to answer 'have we built X?'. "
            "Matches curated capabilities, tech, patterns, reuse_tags, components, and "
            "prose across all documented repos. Returns ranked hits with slug, title, "
            "one_liner, score, the fields that matched, and repo_url."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Capability/tech/pattern to find (e.g. 'fail-closed LLM gate', 'websocket audio ingestion')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "portfolio_reuse_check",
        "description": (
            "BEFORE building something new, scan the portfolio for existing repos to "
            "reuse/extend/link/take inspiration from. Accepts a short description OR a "
            "path to a design doc/plan. Returns ranked candidates with provenance "
            "(why each matched + score) or verdict 'greenfield' when nothing is close."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "building": {"type": "string", "description": "What you're about to build — a description or a path to a design doc/plan"},
                "k": {"type": "integer", "description": "Max candidates (default 5)", "default": 5},
                "min_score": {"type": "number", "description": "Similarity floor 0-1 (default 0.5)", "default": 0.5},
            },
            "required": ["building"],
        },
    },
    {
        "name": "portfolio_record_reuse",
        "description": (
            "Record a reuse decision after a reuse_check, building the repo→repo reuse "
            "graph. relation is one of reuse|extend|link|inspired|new. Use 'new' with a "
            "note when nothing fit (records why, so it isn't re-litigated later)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "built": {"type": "string", "description": "Slug/name of the thing being built"},
                "reused": {"type": "array", "items": {"type": "string"}, "description": "Repo names reused (empty for relation=new)"},
                "relation": {"type": "string", "enum": ["reuse", "extend", "link", "inspired", "new"]},
                "note": {"type": "string", "description": "One line on how/why"},
                "session": {"type": "string", "description": "Session ID, if any"},
            },
            "required": ["built", "relation"],
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


def _handle_portfolio_search(store: Any, embedder: Any, args: dict) -> list[dict]:
    """Execute portfolio_search tool."""
    query = args.get("query", "")
    limit = args.get("limit", args.get("top_k", 10))

    if not query:
        raise ValueError("query is required")

    _check_index(store)

    query_vec = embedder.embed_text(query)
    raw = store.search(query_vec, limit=limit * 3)

    db = store.connect()
    repo_meta: dict[str, dict] = {}
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

    best: dict[str, dict] = {}
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


def _handle_portfolio_clusters(store: Any, _args: dict) -> list[dict]:
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


def _handle_portfolio_find_docs(docs_feed: str, args: dict) -> list[dict]:
    """Execute portfolio_find_docs — search the L0 docs feed (projects.json)."""
    from ghps.docsgen.search_docs import load_feed, search_docs

    query = args.get("query", "")
    if not query:
        raise ValueError("query is required")
    limit = args.get("limit", 10)

    projects = load_feed(docs_feed)
    if not projects:
        raise ValueError(
            f"No docs feed found at {docs_feed}. Run 'ghps gen-docs' to build it."
        )
    return search_docs(projects, query, limit=limit)


def _handle_portfolio_reuse_check(store: Any, embedder: Any, docs_feed: str, args: dict) -> dict:
    """Execute portfolio_reuse_check — surface reusable existing repos with provenance."""
    from ghps.docsgen.search_docs import load_feed
    from ghps.reuse import reuse_check

    building = args.get("building", "")
    if not building:
        raise ValueError("building is required")
    projects = load_feed(docs_feed)
    return reuse_check(
        store, embedder, projects, building,
        k=args.get("k", 5), min_score=args.get("min_score", 0.5),
    )


def _handle_portfolio_record_reuse(ledger_path: str, args: dict) -> dict:
    """Execute portfolio_record_reuse — append a reuse decision to the ledger."""
    from ghps.reuse import record_reuse

    return record_reuse(
        ledger_path,
        built=args.get("built", ""),
        reused=args.get("reused", []),
        relation=args.get("relation", ""),
        note=args.get("note", ""),
        session=args.get("session", ""),
    )


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


def handle_message(
    msg: dict,
    store: Any,
    embedder: Any,
    docs_feed: str = "web/data/projects.json",
    ledger_path: str = "web/data/reuse-ledger.jsonl",
) -> dict | None:
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
            elif tool_name == "portfolio_find_docs":
                result = _handle_portfolio_find_docs(docs_feed, arguments)
            elif tool_name == "portfolio_reuse_check":
                result = _handle_portfolio_reuse_check(store, embedder, docs_feed, arguments)
            elif tool_name == "portfolio_record_reuse":
                result = _handle_portfolio_record_reuse(ledger_path, arguments)
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


def _read_message(stream) -> dict | None:
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


def run_stdio(db_path: str, docs_feed: str = "web/data/projects.json",
              ledger_path: str = "web/data/reuse-ledger.jsonl") -> None:
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

            response = handle_message(msg, store, embedder, docs_feed, ledger_path)
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
    parser.add_argument(
        "--docs-feed",
        type=str,
        default="web/data/projects.json",
        help="Path to the L0 docs feed for portfolio_find_docs (default: web/data/projects.json)",
    )
    parser.add_argument(
        "--reuse-ledger",
        type=str,
        default="web/data/reuse-ledger.jsonl",
        help="Path to the reuse-decision ledger (default: web/data/reuse-ledger.jsonl)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    run_stdio(args.db, args.docs_feed, args.reuse_ledger)


if __name__ == "__main__":
    main()
