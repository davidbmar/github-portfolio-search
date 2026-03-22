"""Search analytics for GitHub Portfolio Search.

Tracks search queries, result counts, and sources in a separate SQLite
database (~/.ghps/analytics.db) so analytics data is independent of the
main vector index.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


_DEFAULT_DB_PATH = os.path.join(Path.home(), ".ghps", "analytics.db")


def _get_db_path(db_path: str | None = None) -> str:
    return db_path or _DEFAULT_DB_PATH


def _ensure_dir(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open (and auto-create) the analytics database."""
    path = _get_db_path(db_path)
    _ensure_dir(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS search_events (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            query     TEXT    NOT NULL,
            timestamp TEXT    NOT NULL,
            result_count INTEGER NOT NULL DEFAULT 0,
            source    TEXT    NOT NULL DEFAULT 'unknown'
        )
        """
    )
    conn.commit()
    return conn


def log_search(
    query: str,
    result_count: int,
    source: str,
    *,
    db_path: str | None = None,
) -> None:
    """Record a search event.

    Args:
        query: The search query string.
        result_count: Number of results returned.
        source: Origin of the search — web, api, mcp, or cli.
        db_path: Override the default analytics DB path (useful for tests).
    """
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO search_events (query, timestamp, result_count, source) VALUES (?, ?, ?, ?)",
            (query, datetime.now(timezone.utc).isoformat(), result_count, source),
        )
        conn.commit()
    finally:
        conn.close()


def get_popular_queries(
    limit: int = 20, *, db_path: str | None = None
) -> list[dict]:
    """Return the most frequently searched queries.

    Returns:
        List of dicts with keys: query, count.
    """
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT query, COUNT(*) AS cnt FROM search_events GROUP BY query ORDER BY cnt DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"query": r["query"], "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


def get_recent_queries(
    limit: int = 100, *, db_path: str | None = None
) -> list[dict]:
    """Return the most recent search events.

    Returns:
        List of dicts with keys: query, timestamp, result_count, source.
    """
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT query, timestamp, result_count, source FROM search_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "query": r["query"],
                "timestamp": r["timestamp"],
                "result_count": r["result_count"],
                "source": r["source"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_search_stats(*, db_path: str | None = None) -> dict:
    """Return aggregate search statistics.

    Returns:
        Dict with keys: total_searches, unique_queries, avg_results,
        top_queries, searches_today.
    """
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT query) AS uniq, AVG(result_count) AS avg_res FROM search_events"
        ).fetchone()

        total = row["total"] or 0
        unique = row["uniq"] or 0
        avg_results = round(row["avg_res"], 2) if row["avg_res"] is not None else 0.0

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM search_events WHERE timestamp LIKE ?",
            (f"{today}%",),
        ).fetchone()
        searches_today = today_row["cnt"] if today_row else 0

        top_rows = conn.execute(
            "SELECT query, COUNT(*) AS cnt FROM search_events GROUP BY query ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        top_queries = [{"query": r["query"], "count": r["cnt"]} for r in top_rows]

        return {
            "total_searches": total,
            "unique_queries": unique,
            "avg_results": avg_results,
            "top_queries": top_queries,
            "searches_today": searches_today,
        }
    finally:
        conn.close()
