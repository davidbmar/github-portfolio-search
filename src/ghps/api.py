"""FastAPI REST API for GitHub Portfolio Search."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import subprocess
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ghps.store import VectorStore
from ghps.embeddings import EmbeddingPipeline
from ghps.clusters import ClusterEngine
from ghps import auth

logger = logging.getLogger(__name__)

# Admin token from environment variable for protecting admin endpoints
ADMIN_TOKEN = os.environ.get("GHPS_ADMIN_TOKEN", "")

# Module-level state, initialized during lifespan
_store: VectorStore | None = None
_embedder: EmbeddingPipeline | None = None


def _ok(data: object) -> dict:
    return {"ok": True, "data": data}


def _err(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status)


_NO_INDEX_MSG = "No index found. Run ghps index first."


def _is_no_table_error(exc: Exception) -> bool:
    """Check if an exception is a 'no such table' OperationalError from any sqlite3 variant."""
    return "OperationalError" in type(exc).__name__ and "no such table" in str(exc)


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

    try:
        query_vec = _embedder.embed_text(q)
        raw = _store.search(query_vec, limit=top_k * 3)
    except Exception as exc:
        if _is_no_table_error(exc):
            return JSONResponse({"results": [], "error": _NO_INDEX_MSG})
        raise

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

    try:
        engine = ClusterEngine(_store)
        cluster_list = engine.cluster_repos(n_clusters=10)
    except Exception as exc:
        if _is_no_table_error(exc):
            return JSONResponse({"results": [], "error": _NO_INDEX_MSG})
        raise

    data = [
        {"name": c.name, "repos": c.repos, "size": len(c.repos)}
        for c in cluster_list
    ]
    return _ok({"clusters": data, "count": len(data)})


@app.get("/api/repos/{slug}")
async def repo_detail(slug: str):
    if _store is None:
        return _err("Store not initialized", 503)

    try:
        db = _store.connect()
        repo_row = db.execute(
            "SELECT name, description, language, topics, stars, updated_at, url FROM repos WHERE name = ?",
            (slug,),
        ).fetchone()
    except Exception as exc:
        if _is_no_table_error(exc):
            return JSONResponse({"results": [], "error": _NO_INDEX_MSG})
        raise

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


# ---------------------------------------------------------------------------
# Auth & access request models
# ---------------------------------------------------------------------------

class AuthVerifyRequest(BaseModel):
    token: str

class AccessRequestBody(BaseModel):
    email: str
    name: str
    reason: str = ""

class AccessActionBody(BaseModel):
    email: str


def _check_admin(authorization: str | None) -> bool:
    """Return True if the Authorization header carries a valid admin token."""
    if not ADMIN_TOKEN:
        return False
    if not authorization:
        return False
    # Accept "Bearer <token>" or raw token
    token = authorization.removeprefix("Bearer ").strip()
    return token == ADMIN_TOKEN


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/verify")
async def auth_verify(body: AuthVerifyRequest):
    """Verify a Google OAuth JWT and return user info + approval status."""
    try:
        user_info = auth.verify_token(body.token)
    except ValueError as exc:
        return _err(str(exc), 401)
    approved = auth.is_approved(user_info["email"])
    return _ok({"user": user_info, "approved": approved})


@app.post("/api/access/request")
async def access_request(body: AccessRequestBody):
    """Submit an access request (stores in pending list)."""
    auth.add_pending_request(body.email, body.name, body.reason)
    return _ok({"message": "Access request submitted"})


@app.get("/api/access/pending")
async def access_pending(authorization: str | None = Header(default=None)):
    """Return pending access requests (admin only)."""
    if not _check_admin(authorization):
        return _err("Unauthorized", 403)
    pending = auth.get_pending_requests()
    return _ok({"pending": pending})


@app.post("/api/access/approve")
async def access_approve(
    body: AccessActionBody,
    authorization: str | None = Header(default=None),
):
    """Approve an email for access (admin only)."""
    if not _check_admin(authorization):
        return _err("Unauthorized", 403)
    auth.approve_email(body.email)
    return _ok({"message": f"{body.email} approved"})


@app.post("/api/access/deny")
async def access_deny(
    body: AccessActionBody,
    authorization: str | None = Header(default=None),
):
    """Deny/remove a pending access request (admin only)."""
    if not _check_admin(authorization):
        return _err("Unauthorized", 403)
    auth.deny_email(body.email)
    return _ok({"message": f"{body.email} denied"})


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
