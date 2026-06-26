from __future__ import annotations

from ..github_client import fetch_pr_files
from .cluster import classify_pr, pr_embed_text
from .mature import apply_lifecycle
from .reduce import build_pr_record
from .render import write_learn_pages, write_tutorial_prose
from .scan import scan_repo


def run(owner, repos, store, client, embedder, out_dir, *, model,
        fetch_files=fetch_pr_files, scan_fn=scan_repo) -> dict:
    pr_count = 0
    for repo in repos:
        for pr in scan_fn(owner, repo, store):
            pr["repo"] = repo
            files = fetch_files(owner, repo, pr["number"])
            rec = build_pr_record(pr, files, client, model=model)
            store.put_pr(rec)
            pr_count += 1
            vec = embedder.embed_text(pr_embed_text(rec))
            classify_pr(rec, vec, store, client, model=model)

    matured = apply_lifecycle(store)
    for theme in matured:
        write_tutorial_prose(theme, store.all_prs(), client, model=model)
        store.put_theme(theme)
    pages = write_learn_pages(matured, out_dir) if matured else []
    return {"prs": pr_count, "themes_matured": len(matured), "pages": pages}
