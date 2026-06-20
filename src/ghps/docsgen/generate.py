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
from ghps.docsgen import aggregate, context, markdown, record_gen, render, search_index
from ghps.docsgen._util import utc_z
from ghps.docsgen.record_gen import RecordGenerationError

logger = logging.getLogger(__name__)

# Where the published docs live (used to build absolute URLs in llms.txt).
BASE_URL = "https://davidbmar.com"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, data) -> None:
    _write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# Repo-side convention: publishable HTML lives under docs/html/. On the site it
# is served at projects/<slug>/docs/<rel>, dropping the "html" implementation
# detail. Kept in sync with github_client.DOCS_HTML_PREFIX.
_DOCS_HTML_PREFIX = "docs/html/"
_DOCS_MD_PREFIX = "docs/md/"


def _clean_rel_parts(path: str, prefix: str) -> list[str] | None:
    """Strip *prefix*, split, and reject path traversal. None if unsafe/empty."""
    rel = path[len(prefix):] if path.startswith(prefix) else path
    parts = [seg for seg in rel.split("/") if seg not in ("", ".")]
    if not parts or any(seg == ".." for seg in parts):
        return None
    return parts


def _safe_doc_rel(path: str) -> str | None:
    """Normalize a ``docs/html/...`` repo path to a site path under ``<slug>/docs/``.

    Returns the cleaned ``.html`` relative path, or None to skip. The doc HTML
    comes from GitHub, so the path is not trusted.
    """
    parts = _clean_rel_parts(path, _DOCS_HTML_PREFIX)
    if parts is None:
        return None
    rel = "/".join(parts)
    return rel if rel.lower().endswith(".html") else None


def _safe_md_rel(path: str) -> str | None:
    """Normalize a ``docs/md/...md`` repo path to the rendered ``.html`` site rel.

    e.g. ``docs/md/sub/roadmap.md`` -> ``sub/roadmap.html`` (written under
    ``<slug>/docs/md/``). Rejects traversal and non-``.md`` paths.
    """
    parts = _clean_rel_parts(path, _DOCS_MD_PREFIX)
    if parts is None:
        return None
    rel = "/".join(parts)
    if not rel.lower().endswith(".md"):
        return None
    return rel[: -len(".md")] + ".html"


def _is_stale(record_path: Path, pushed_at: str) -> bool:
    """True if the repo was pushed after the record was generated.

    Both timestamps are ISO-8601 UTC with a 'Z' suffix, so a lexicographic
    comparison is correct. An unreadable record is treated as stale (regenerate).
    """
    if not pushed_at:
        return False
    try:
        generated_at = json.loads(record_path.read_text()).get("generated_at", "")
    except (OSError, json.JSONDecodeError):
        return True
    return bool(generated_at) and pushed_at > generated_at


def generate_one(
    repo_meta: dict,
    *,
    owner: str,
    records_dir: str,
    client,
    gh=_default_gh,
    model: str | None = None,
) -> dict:
    """Generate + persist the record for a single repo (no rendering).

    Rendering to HTML/feeds is decoupled into :func:`publish_all`, so the web
    artifacts can be rebuilt from records without re-calling the LLM.
    """
    ctx = context.build_context(repo_meta, owner=owner, gh=gh)
    record = record_gen.generate_record(ctx, client, model=model)

    record_path = Path(records_dir) / f"{record['slug']}.record.json"
    _write_json(record_path, record)
    logger.info("generated %s", record["slug"])
    return record


def publish_all(
    *,
    records_dir: str,
    html_dir: str,
    feed_path: str,
    base_url: str = BASE_URL,
) -> dict:
    """Render ALL web artifacts from the records on disk — no LLM calls.

    Produces, for AI + human consumption (progressive disclosure):
      - per-repo:  <html_dir>/<slug>.html  and  <html_dir>/<slug>.record.json (Tier 2)
      - <feed_dir>/projects.json        — full corpus (last resort)
      - <feed_dir>/projects-index.json  — compact index (Tier 1)
      - <html_dir>/index.html           — human listing page
      - <web_root>/llms.txt             — discovery manifest (Tier 0)
    """
    summary = aggregate.aggregate_records(records_dir, feed_path)
    projects = summary["projects"]
    hd = Path(html_dir)
    hd.mkdir(parents=True, exist_ok=True)

    for p in projects:
        slug = p.get("slug")
        if not slug:
            continue
        _write_text(hd / f"{slug}.html", render.render_page(p))
        _write_json(hd / f"{slug}.record.json", p)

        # Republish the project's own docs under <slug>/docs/: HTML docs verbatim
        # at <slug>/docs/<rel>, Markdown docs rendered to HTML at <slug>/docs/md/
        # <rel>. Generate a combined index plus per-kind listing pages.
        html_rels: list[str] = []
        md_rels: list[str] = []
        for d in p.get("docs") or []:
            kind = d.get("kind") or ("md" if "markdown" in d else "html")
            if kind == "md":
                rel = _safe_md_rel(d.get("path", ""))
                if rel is None:
                    continue
                body = markdown.render(d.get("markdown", "") or "")
                page = render.render_markdown_doc_page(p, rel, body)
                _write_text(hd / slug / "docs" / "md" / rel, page)
                md_rels.append(rel)
            else:
                rel = _safe_doc_rel(d.get("path", ""))
                if rel is None:
                    continue
                _write_text(hd / slug / "docs" / rel, d.get("html", "") or "")
                html_rels.append(rel)

        if html_rels or md_rels:
            docs_index_html = render.render_docs_index_page(p, html_rels, md_rels)
            # The combined index — unless the repo shipped its own docs/index.html.
            if "index.html" not in html_rels:
                _write_text(hd / slug / "docs" / "index.html", docs_index_html)
            # Flat copy so the no-trailing-slash URL resolves: the CF rewrite turns
            # /projects/<slug>/docs into <slug>/docs.html. Root-absolute links work
            # from either location.
            _write_text(hd / slug / "docs.html", docs_index_html)
            # Per-kind listing pages: /docs/html and /docs/md (flat .html so the
            # extensionless URLs resolve via the same CF rewrite).
            if html_rels:
                _write_text(
                    hd / slug / "docs" / "html.html",
                    render.render_docs_kind_page(p, "html", html_rels),
                )
            if md_rels:
                _write_text(
                    hd / slug / "docs" / "md.html",
                    render.render_docs_kind_page(p, "md", md_rels),
                )

    aggregate.write_compact_index(
        projects, str(Path(feed_path).parent / "projects-index.json")
    )
    # Single source of truth for the web SPA's client-side search — a rich
    # index over ALL projects (incl. private ones the GitHub indexer misses).
    search_index.write_search_index(
        projects, str(Path(feed_path).parent / "projects-search.json")
    )
    _write_text(hd / "index.html", render.render_index_page(projects))
    _write_text(
        hd.parent / "llms.txt",
        render.render_llms_txt(projects, base_url=base_url, generated_at=utc_z()),
    )
    logger.info("published %d project docs to %s", len(projects), html_dir)
    return {"published": len(projects)}


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
    stale: bool = False,
    model: str | None = None,
) -> dict:
    """Generate docs for every repo owned by *owner*.

    Idempotent: an existing record is skipped unless *force* (regenerate all) or
    *stale* (regenerate only repos whose GitHub ``pushed_at`` is newer than the
    record's ``generated_at`` — i.e. checked-in since the doc was written).

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
            if not (stale and _is_stale(record_path, repo_meta.get("pushed_at", ""))):
                skipped += 1
                logger.info("skipping %s (record exists)", slug)
                continue
            logger.info("regenerating %s (pushed since last generated)", slug)
        try:
            generate_one(
                repo_meta,
                owner=owner,
                records_dir=records_dir,
                client=client,
                gh=gh,
                model=model,
            )
            generated += 1
        except (RecordGenerationError, KeyError, OSError) as exc:
            logger.warning("FAILED %s: %s", slug, exc)
            failed.append(slug)

    # Render every web artifact from the records on disk (not just this run).
    publish_all(records_dir=records_dir, html_dir=html_dir, feed_path=feed_path)

    return {"generated": generated, "skipped": skipped, "failed": failed}
