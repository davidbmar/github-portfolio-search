"""CLI interface for GitHub Portfolio Search."""

from __future__ import annotations

import os
from pathlib import Path

import click


DEFAULT_DB = os.path.join(Path.home(), ".ghps", "index.db")


@click.group()
def main() -> None:
    """ghps - GitHub Portfolio Search."""


@main.command()
@click.argument("query")
@click.option("--top-k", default=10, help="Number of results to return.")
@click.option("--db", default=DEFAULT_DB, help="Path to the SQLite-vec database.")
def search(query: str, top_k: int, db: str) -> None:
    """Search indexed repos by semantic similarity."""
    from ghps.embeddings import EmbeddingPipeline
    from ghps.search import SearchEngine
    from ghps.store import VectorStore

    store = VectorStore(db)
    embedder = EmbeddingPipeline()
    engine = SearchEngine(store, embedder)

    results = engine.search(query, top_k=top_k)

    if not results:
        click.echo("No results found.")
        return

    for i, r in enumerate(results, 1):
        snippet = r.chunk_text[:200]
        click.echo(f"\n{'='*60}")
        click.echo(f"  #{i}  {r.repo_name}  (score: {r.score:.4f})")
        click.echo(f"  URL: {r.repo_url}")
        click.echo(f"  Source: {r.source}")
        click.echo(f"  {snippet}")
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


if __name__ == "__main__":
    main()
