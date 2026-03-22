"""FastAPI REST API for GitHub Portfolio Search."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import subprocess
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ghps.store import VectorStore
from ghps.embeddings import EmbeddingPipeline
from ghps.clusters import ClusterEngine

logger = logging.getLogger(__name__)

# Module-level state, initialized during lifespan
_store: VectorStore | None = None
_embedder: EmbeddingPipeline | None = None


def _ok(data: object) -> dict:
    return {"ok": True, "data": data}


def _err(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the vector store on startup, close on shutdown."""
    global _store, _embedder
    db_path = app.state.db_path if hasattr(app.state, "db_path") else "ghps.db"
    _store = VectorStore(db_path)
    _store.connect()
    _embedder = EmbeddingPipeline()
    logger.info("API started — db=%s", db_path)
    yield
    if _store:
        _store.close()
    logger.info("API shutdown")


app = FastAPI(title="GitHub Portfolio Search API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return _ok({"status": "healthy"})


@app.get("/api/search")
async def search(q: str = Query(..., min_length=1), top_k: int = Query(10, ge=1, le=100)):
    if _store is None or _embedder is None:
        return _err("Store not initialized", 503)

    query_vec = _embedder.embed_text(q)
    raw = _store.search(query_vec, limit=top_k * 3)

    db = _store.connect()

    # Deduplicate: keep best chunk per repo
    best: dict[str, dict] = {}
    for row in raw:
        repo_name = row["repo_name"]
        score = 1.0 - row["distance"]
        if repo_name not in best or score > best[repo_name]["score"]:
            best[repo_name] = {
                "repo_name": repo_name,
                "score": round(score, 4),
                "snippet": row["text"][:300],
                "source": row["source"],
            }

    # Enrich with repo metadata
    results = []
    for item in sorted(best.values(), key=lambda x: x["score"], reverse=True)[:top_k]:
        repo_row = db.execute(
            "SELECT description, url FROM repos WHERE name = ?", (item["repo_name"],)
        ).fetchone()
        item["description"] = repo_row[0] if repo_row else ""
        item["url"] = repo_row[1] if repo_row else ""
        results.append(item)

    return _ok({"results": results, "query": q, "count": len(results)})


@app.get("/api/clusters")
async def clusters():
    if _store is None:
        return _err("Store not initialized", 503)

    engine = ClusterEngine(_store)
    cluster_list = engine.cluster_repos(n_clusters=10)

    data = [
        {"name": c.name, "repos": c.repos, "size": len(c.repos)}
        for c in cluster_list
    ]
    return _ok({"clusters": data, "count": len(data)})


@app.get("/api/repos/{slug}")
async def repo_detail(slug: str):
    if _store is None:
        return _err("Store not initialized", 503)

    db = _store.connect()
    repo_row = db.execute(
        "SELECT name, description, language, topics, stars, updated_at, url FROM repos WHERE name = ?",
        (slug,),
    ).fetchone()

    if not repo_row:
        return _err(f"Repo '{slug}' not found", 404)

    topics = []
    try:
        topics = json.loads(repo_row[3]) if repo_row[3] else []
    except (json.JSONDecodeError, TypeError):
        pass

    # Get README excerpt from chunks
    readme_chunks = db.execute(
        "SELECT text FROM chunks WHERE repo_name = ? AND source LIKE '%README%' ORDER BY id LIMIT 3",
        (slug,),
    ).fetchall()
    readme_excerpt = "\n\n".join(r[0] for r in readme_chunks) if readme_chunks else ""

    # Get matched chunks (all chunks for this repo)
    all_chunks = db.execute(
        "SELECT source, text FROM chunks WHERE repo_name = ? ORDER BY id",
        (slug,),
    ).fetchall()

    return _ok({
        "name": repo_row[0],
        "description": repo_row[1],
        "language": repo_row[2],
        "topics": topics,
        "stars": repo_row[4],
        "updated_at": repo_row[5],
        "url": repo_row[6],
        "readme_excerpt": readme_excerpt[:2000],
        "chunks": [{"source": c[0], "text": c[1][:500]} for c in all_chunks],
    })


def _kill_stale_server(port: int) -> None:
    """Kill any existing process on the given port."""
    try:
        pids = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
        for pid in pids.splitlines():
            pid_int = int(pid)
            if pid_int != os.getpid():
                os.kill(pid_int, signal.SIGTERM)
    except (subprocess.CalledProcessError, OSError):
        pass


def main():
    """Entry point for ghps-server console script."""
    import uvicorn

    parser = argparse.ArgumentParser(description="GitHub Portfolio Search API server")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--db", type=str, default="ghps.db", help="Path to SQLite database")
    args = parser.parse_args()

    _kill_stale_server(args.port)

    app.state.db_path = args.db
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting ghps-server on port %d with db=%s", args.port, args.db)

    uvicorn.run(app, host="0.0.0.0", port=args.port)
