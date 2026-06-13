"""Orchestrate L0 doc generation across one or many repos.

Idempotent: skips repos whose record already exists unless force=True. Writes
the record (projects/<slug>.record.json), the HTML page (web/projects/<slug>.html),
and finally aggregates all records into the machine feed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ghps import github_client as _default_gh
from ghps.docsgen import aggregate, context, record_gen, render
from ghps.docsgen.record_gen import RecordGenerationError

logger = logging.getLogger(__name__)


def generate_one(
    repo_meta: dict,
    *,
    owner: str,
    records_dir: str,
    html_dir: str,
    client,
    gh=_default_gh,
    model: str | None = None,
) -> dict:
    """Generate record + HTML for a single repo. Returns the record dict."""
    ctx = context.build_context(repo_meta, owner=owner, gh=gh)
    record = record_gen.generate_record(ctx, client, model=model)

    Path(records_dir).mkdir(parents=True, exist_ok=True)
    Path(html_dir).mkdir(parents=True, exist_ok=True)

    record_path = Path(records_dir) / f"{record['slug']}.record.json"
    record_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    html_path = Path(html_dir) / f"{record['slug']}.html"
    html_path.write_text(render.render_page(record))

    logger.info("generated %s", record["slug"])
    return record


def generate_all(
    *,
    owner: str,
    records_dir: str,
    html_dir: str,
    feed_path: str,
    client,
    gh=_default_gh,
    only: str | None = None,
    limit: int | None = None,
    force: bool = False,
    model: str | None = None,
) -> dict:
    """Generate docs for every repo owned by *owner*.

    Returns ``{"generated": int, "skipped": int, "failed": list[str]}``.
    """
    repos = gh.fetch_repos(owner)
    if only:
        repos = [r for r in repos if r["name"] == only]
    if limit is not None:
        repos = repos[:limit]

    generated = 0
    skipped = 0
    failed: list[str] = []

    for repo_meta in repos:
        slug = repo_meta["name"]
        record_path = Path(records_dir) / f"{slug}.record.json"
        if record_path.exists() and not force:
            skipped += 1
            logger.info("skipping %s (record exists)", slug)
            continue
        try:
            generate_one(
                repo_meta,
                owner=owner,
                records_dir=records_dir,
                html_dir=html_dir,
                client=client,
                gh=gh,
                model=model,
            )
            generated += 1
        except (RecordGenerationError, KeyError, OSError) as exc:
            logger.warning("FAILED %s: %s", slug, exc)
            failed.append(slug)

    aggregate.aggregate_records(records_dir, feed_path)
    return {"generated": generated, "skipped": skipped, "failed": failed}
