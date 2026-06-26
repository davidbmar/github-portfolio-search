from __future__ import annotations

from ..github_client import fetch_pr_files
from .cluster import classify_pr, pr_embed_text
from .mature import apply_lifecycle
from .reduce import build_pr_record
from .render import write_learn_pages, write_tutorial_prose
from .scan import scan_repo
from .schema import NarrateValidationError


def run(owner, repos, store, client, embedder, out_dir, *, model,
        fetch_files=fetch_pr_files, scan_fn=scan_repo) -> dict:
    pr_count = 0
    pr_failed = 0
    for repo in repos:
        new_prs = scan_fn(owner, repo, store)   # ascending by merged_at, already-stored filtered out
        advance = store.read_cursor(repo)
        frozen = False
        for pr in new_prs:
            pr["repo"] = repo
            try:
                files = fetch_files(owner, repo, pr["number"])
                rec = build_pr_record(pr, files, client, model=model)
                store.put_pr(rec)
                vec = embedder.embed_text(pr_embed_text(rec))
                classify_pr(rec, vec, store, client, model=model)
                pr_count += 1
                if not frozen and (advance is None or pr["merged_at"] > advance):
                    advance = pr["merged_at"]
            except Exception:
                frozen = True          # do not advance past an unstored PR; retry it next run
                pr_failed += 1
                continue
        if advance and advance != store.read_cursor(repo):
            store.write_cursor(repo, advance)

    matured = apply_lifecycle(store)
    to_publish = [t for t in matured if t.get("status") == "mature"]
    failed = 0
    for theme in to_publish:
        try:
            write_tutorial_prose(theme, store.all_prs(), client, model=model)
        except NarrateValidationError:
            failed += 1
            continue                      # leave status 'mature'; retry next run
        theme["status"] = "published"
        store.put_theme(theme)
    published = [t for t in store.all_themes() if t.get("status") == "published"]
    pages = write_learn_pages(published, out_dir) if published else []
    return {"prs": pr_count, "pr_failed": pr_failed,
            "themes_published": len(to_publish) - failed,
            "themes_matured": len(to_publish), "pages": pages, "themes_failed": failed}
