"""CLI interface for GitHub Portfolio Search."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click


def _load_dotenv() -> None:
    """Load .env file from project root if it exists."""
    # Walk up from this file to find .env
    here = Path(__file__).resolve().parent
    for candidate in [here.parent.parent, Path.cwd()]:
        env_file = candidate / ".env"
        if env_file.is_file():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip())
            break


_load_dotenv()

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
    # Suppress model-loading progress bars so they don't corrupt stdout
    # (especially important for --format json).
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
    import logging
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

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

    # Log search to analytics if available (analytics.py is provided by agentB)
    try:
        from ghps.analytics import log_search
        log_search(query=query, num_results=len(results), source="cli")
    except (ImportError, Exception):
        pass  # analytics module not yet available

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
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format.")
def stats(fmt: str) -> None:
    """Show search analytics summary (total searches, top queries, avg results)."""
    try:
        from ghps.analytics import get_analytics_summary
    except ImportError:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Analytics module not available.\n"
            + "The analytics feature requires the analytics module (analytics.py).",
            err=True,
        )
        sys.exit(1)

    summary = get_analytics_summary()

    if fmt == "json":
        click.echo(json.dumps(summary, indent=2))
        return

    click.echo(click.style("\n  Search Analytics", fg="cyan", bold=True))
    click.echo(f"  {'='*40}")
    click.echo(click.style("  Total searches:  ", fg="white") + str(summary.get("total_searches", 0)))
    click.echo(click.style("  Avg results:     ", fg="white") + f"{summary.get('avg_results', 0):.1f}")
    top_queries = summary.get("top_queries", [])
    if top_queries:
        click.echo(click.style("  Top queries:", fg="white"))
        for q in top_queries[:5]:
            click.echo(f"    - {q.get('query', '?')} ({q.get('count', 0)} times)")
    else:
        click.echo(click.style("  Top queries:     ", fg="white") + "none yet")
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


@main.command(name="gen-docs")
@click.option("--owner", default="davidbmar", help="GitHub owner/org to document.")
@click.option("--only", default=None, help="Generate just one repo by slug.")
@click.option("--limit", default=None, type=int, help="Cap number of repos (cost control).")
@click.option("--force", is_flag=True, help="Regenerate even if a record exists.")
@click.option("--stale", is_flag=True, help="Regenerate only repos pushed since their doc was generated.")
@click.option("--provider", default=None, help="LLM provider (dashscope|anthropic).")
@click.option("--model", default=None, help="Override model id (provenance + dial).")
def gen_docs(owner, only, limit, force, stale, provider, model):
    """Generate AI-written, machine-readable docs (L0) for each repo."""
    from ghps.docsgen import generate
    from ghps.docsgen.llm_client import get_client

    # The model id (when given) propagates via the generate_all kwarg, which
    # takes precedence inside generate_record — no need to mutate the client.
    client = get_client(provider)

    result = generate.generate_all(
        owner=owner,
        records_dir="projects",
        html_dir="web/projects",
        feed_path="web/data/projects.json",
        client=client,
        only=only,
        limit=limit,
        force=force,
        stale=stale,
        model=model,
    )

    click.echo(click.style("Doc generation complete!", fg="green", bold=True))
    click.echo(f"  generated: {result['generated']}")
    click.echo(f"  skipped:   {result['skipped']}")
    if result["failed"]:
        click.echo(click.style(f"  failed:    {result['failed']}", fg="red"))
        # Surface partial failure to make / CI chains so a bad run is visible.
        sys.exit(1)


@main.command(name="publish-docs")
def publish_docs():
    """Rebuild all web doc artifacts from existing records (no LLM calls).

    Re-renders HTML pages, the listing page, per-repo record JSON, the full feed,
    the compact index, and /llms.txt from projects/*.record.json. Use after a
    template change or to publish records without regenerating them.
    """
    from ghps.docsgen import generate

    result = generate.publish_all(
        records_dir="projects",
        html_dir="web/projects",
        feed_path="web/data/projects.json",
    )
    click.echo(click.style("Publish complete!", fg="green", bold=True))
    click.echo(f"  published: {result['published']} project docs")


@main.command(name="daily")
@click.option("--owner", default="davidbmar", help="GitHub account to scan.")
@click.option("--since", default=None,
              help="ISO date/time lower bound for commits (e.g. 2026-05-01).")
@click.option("--engine",
              type=click.Choice(
                  ["auto", "codex", "mlx", "mlx-local", "dashscope", "deterministic"]),
              default="auto",
              help="Headline engine. mlx-local = free in-process MLX (Qwen3.5-4B); "
                   "dashscope = Alibaba Qwen cloud (for CI); codex = cloud; "
                   "auto = codex -> mlx server -> deterministic.")
@click.option("--token", default=None, help="GitHub PAT (else GITHUB_TOKEN env).")
@click.option("--no-cache", is_flag=True, default=False,
              help="Regenerate every day, ignoring the cache of unchanged days.")
def daily_cmd(owner, since, engine, token, no_cache):
    """Generate the daily headline digest -> web/data/daily.json + /daily page.

    Aggregates each day's commits across all of *owner*'s repos, generates a
    headline + summary per day via the chosen engine, and renders the /daily feed.
    Days whose commit set is unchanged since the last run are reused from
    web/data/daily.json (no engine call) unless --no-cache is given.
    """
    from pathlib import Path as _Path

    from ghps import daily as daily_mod
    from ghps import github_client
    from ghps.docsgen import render

    if token:
        os.environ["GITHUB_TOKEN"] = token

    eng = daily_mod.resolve_engine(engine)
    click.echo(f"Engine: {type(eng).__name__}")
    click.echo(f"Collecting commits for {owner} since {since or 'the beginning'}...")
    repo_commits = daily_mod.collect(owner, github_client, since=since)
    total = sum(len(v) for v in repo_commits.values())
    click.echo(f"  {total} commits across {len(repo_commits)} repos")

    prior = {}
    daily_path = _Path("web/data/daily.json")
    if not no_cache and daily_path.exists():
        try:
            prior = {d["date"]: d for d in json.loads(daily_path.read_text())["days"]}
            click.echo(f"  cache: {len(prior)} prior days loaded "
                       "(unchanged days will be reused)")
        except (OSError, json.JSONDecodeError, KeyError):
            prior = {}

    click.echo("Generating per-day headlines (cached days skip the engine)...")
    days = daily_mod.build_digests(repo_commits, eng, prior=prior)
    reused = sum(1 for d in days if d["date"] in prior
                 and prior[d["date"]] is d)
    click.echo(f"  reused {reused} cached days, generated {len(days) - reused}")
    path = daily_mod.write_daily(days, "web/data/daily.json")
    click.echo(f"  wrote {path} ({len(days)} days)")

    daily_html = render.render_daily_page(days)
    _Path("web/daily").mkdir(parents=True, exist_ok=True)
    _Path("web/daily/index.html").write_text(daily_html, encoding="utf-8")
    _Path("web/daily.html").write_text(daily_html, encoding="utf-8")
    click.echo(click.style(f"Daily digest done: {len(days)} days.", fg="green", bold=True))


@main.command(name="narrate")
@click.option("--owner", default="davidbmar", help="GitHub owner/org.")
@click.option("--repos", required=True, help="Comma-separated repo slugs.")
@click.option("--out", "out_dir", default="web/learn", help="Output dir for /learn pages.")
@click.option("--state", "state_dir", default="web/data/narrate", help="State dir.")
@click.option("--provider", default=None, help="LLM provider (dashscope|anthropic).")
@click.option("--model", default=None, help="Override model id.")
def narrate(owner, repos, out_dir, state_dir, provider, model):
    """Generate theme-grouped applied tutorials from merged PRs."""
    from .narrate import pipeline
    from .narrate.store import Store
    repo_list = [r.strip() for r in repos.split(",") if r.strip()]
    client = _narrate_client(provider, model)
    embedder = _narrate_embedder()
    eff_model = model or os.environ.get("DASHSCOPE_MODEL", "qwen-plus")
    summary = pipeline.run(owner, repo_list, Store(state_dir), client, embedder,
                           out_dir, model=eff_model)
    click.echo(f"narrate: {summary['prs']} PRs, "
               f"{summary['themes_matured']} themes matured, "
               f"{len(summary['pages'])} pages written")


def _narrate_client(provider, model):
    from .docsgen.llm_client import DashScopeClient, AnthropicClient
    if provider == "anthropic":
        return AnthropicClient()
    return DashScopeClient()


def _narrate_embedder():
    from .embeddings import EmbeddingPipeline
    return EmbeddingPipeline()


@main.command(name="find-docs")
@click.argument("query")
@click.option("--feed", default="web/data/projects.json", help="Path to the L0 docs feed.")
@click.option("--top-k", default=10, help="Number of results.")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def find_docs(query, feed, top_k, fmt):
    """Search the generated project docs (L2): 'have we built X?'."""
    from ghps.docsgen.search_docs import load_feed, search_docs

    projects = load_feed(feed)
    if not projects:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"No docs feed at {feed}. Run 'ghps gen-docs' first.",
            err=True,
        )
        sys.exit(1)

    hits = search_docs(projects, query, limit=top_k)

    if fmt == "json":
        click.echo(json.dumps(hits, indent=2))
        return

    if not hits:
        click.echo(f'No project docs match "{query}".')
        return

    click.echo(
        click.style(f"\n  {len(hits)} match(es) for ", fg="white")
        + click.style(f'"{query}"', fg="cyan", bold=True)
    )
    for h in hits:
        click.echo(
            f"\n  {click.style(h['title'], fg='cyan', bold=True)} "
            + click.style(f"(score {h['score']})", fg="green")
        )
        click.echo(f"    {h['one_liner']}")
        click.echo(click.style(f"    matched: ", fg="white") + ", ".join(h["matched"]))
        click.echo(f"    {h['repo_url']}")
    click.echo()


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
