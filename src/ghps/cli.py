"""CLI interface for GitHub Portfolio Search."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click


DEFAULT_DB = os.path.join(Path.home(), ".ghps", "index.db")


def _db_exists(db: str) -> bool:
    """Check if the database file exists (skip check for :memory:)."""
    if db == ":memory:":
        return True
    return os.path.isfile(db)


@click.group()
def main() -> None:
    """ghps - GitHub Portfolio Search."""


@main.command()
@click.argument("query")
@click.option("--top-k", default=10, help="Number of results to return.")
@click.option("--db", default=DEFAULT_DB, help="Path to the SQLite-vec database.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format.")
def search(query: str, top_k: int, db: str, fmt: str) -> None:
    """Search indexed repos by semantic similarity."""
    from ghps.embeddings import EmbeddingPipeline
    from ghps.search import SearchEngine
    from ghps.store import VectorStore

    if not _db_exists(db):
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Index not found at {db}\n"
            + "Run 'ghps index <username>' first to create the index.",
            err=True,
        )
        sys.exit(1)

    store = VectorStore(db)
    embedder = EmbeddingPipeline()
    engine = SearchEngine(store, embedder)

    results = engine.search(query, top_k=top_k)

    if fmt == "json":
        data = [
            {
                "repo_name": r.repo_name,
                "score": round(r.score, 4),
                "source": r.source,
                "url": r.repo_url,
                "snippet": r.chunk_text[:200],
            }
            for r in results
        ]
        click.echo(json.dumps(data, indent=2))
        return

    if not results:
        click.echo("No results found.")
        return

    click.echo(
        click.style(f"\n  Found {len(results)} result(s) for ", fg="white")
        + click.style(f'"{query}"', fg="cyan", bold=True)
    )

    for i, r in enumerate(results, 1):
        snippet = r.chunk_text[:120].replace("\n", " ")
        score_color = "green" if r.score >= 0.8 else "yellow" if r.score >= 0.5 else "red"

        click.echo(f"\n{'='*60}")
        click.echo(
            click.style(f"  #{i}  ", fg="white", bold=True)
            + click.style(r.repo_name, fg="cyan", bold=True)
            + "  "
            + click.style(f"score: {r.score:.4f}", fg=score_color)
        )
        click.echo(click.style(f"  URL:    ", fg="white") + r.repo_url)
        click.echo(click.style(f"  Source: ", fg="white") + r.source)
        click.echo(click.style(f"  ", fg="white") + snippet)
    click.echo()


@main.command()
@click.argument("username")
@click.option("--db", default=DEFAULT_DB, help="Path to the SQLite-vec database.")
@click.option("--token", default=None, help="GitHub personal access token.")
def index(username: str, db: str, token: str | None) -> None:
    """Index all repos for a GitHub user."""
    from ghps.embeddings import EmbeddingPipeline
    from ghps.indexer import Indexer
    from ghps.store import VectorStore
    from ghps import github_client

    if token:
        os.environ["GITHUB_TOKEN"] = token

    db_dir = os.path.dirname(db)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    store = VectorStore(db)
    store.create_index()
    indexer = Indexer(store=store, pipeline=EmbeddingPipeline())
    indexer.index_user(username, github_client=github_client)
    click.echo(f"Indexing complete. Database: {db}")


@main.command()
@click.option("--db", default=DEFAULT_DB, help="Path to the SQLite-vec database.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format.")
def status(db: str, fmt: str) -> None:
    """Show index statistics (repo count, chunk count, last indexed)."""
    from ghps.store import VectorStore

    if not _db_exists(db):
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Index not found at {db}\n"
            + "Run 'ghps index <username>' first to create the index.",
            err=True,
        )
        sys.exit(1)

    store = VectorStore(db)
    db_conn = store.connect()

    repo_count = db_conn.execute("SELECT COUNT(*) FROM repos").fetchone()[0]
    chunk_count = db_conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    last_updated_row = db_conn.execute(
        "SELECT updated_at FROM repos ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    last_updated = last_updated_row[0] if last_updated_row else "N/A"

    store.close()

    if fmt == "json":
        data = {
            "database": db,
            "repo_count": repo_count,
            "chunk_count": chunk_count,
            "last_indexed": last_updated,
        }
        click.echo(json.dumps(data, indent=2))
        return

    click.echo(click.style("\n  Index Status", fg="cyan", bold=True))
    click.echo(f"  {'='*40}")
    click.echo(click.style("  Database:     ", fg="white") + db)
    click.echo(click.style("  Repos:        ", fg="white") + str(repo_count))
    click.echo(click.style("  Chunks:       ", fg="white") + str(chunk_count))
    click.echo(click.style("  Last indexed: ", fg="white") + last_updated)
    click.echo()


@main.command()
@click.option("--db", default=DEFAULT_DB, help="Path to the SQLite-vec database.")
@click.option("--output", default="web/data", help="Output directory for JSON files.")
def export(db: str, output: str) -> None:
    """Export static JSON bundle for the web UI."""
    from ghps.export import export_static_bundle
    from ghps.store import VectorStore

    if not _db_exists(db):
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Index not found at {db}\n"
            + "Run 'ghps index <username>' first to create the index.",
            err=True,
        )
        sys.exit(1)

    store = VectorStore(db)
    store.connect()

    paths = export_static_bundle(store, output)
    store.close()

    click.echo(click.style("Export complete!", fg="green", bold=True))
    for name, path in paths.items():
        click.echo(f"  {name} -> {path}")


@main.command()
@click.option("--port", default=8000, help="Port to listen on.")
@click.option("--db", default=DEFAULT_DB, help="Path to the SQLite-vec database.")
def serve(port: int, db: str) -> None:
    """Start the FastAPI server."""
    import uvicorn
    from ghps.api import app, _kill_stale_server

    if not _db_exists(db):
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Index not found at {db}\n"
            + "Run 'ghps index <username>' first to create the index.",
            err=True,
        )
        sys.exit(1)

    _kill_stale_server(port)
    app.state.db_path = db

    click.echo(
        click.style("Starting server", fg="green", bold=True)
        + f" on port {port} (db: {db})"
    )
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
