from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..github_client import fetch_merged_prs
from .store import Store


def _shift(iso: str | None, days: int) -> str | None:
    if not iso:
        return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")) - timedelta(days=days)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan_repo(owner: str, repo: str, store: Store, *, overlap_days: int = 3, fetch=fetch_merged_prs) -> list[dict]:
    cursor = store.read_cursor(repo)
    since = _shift(cursor, overlap_days)
    candidates = fetch(owner, repo, since=since)
    new: list[dict] = []
    max_merged = cursor
    for pr in candidates:
        max_merged = pr["merged_at"] if (max_merged is None or pr["merged_at"] > max_merged) else max_merged
        if store.get_pr(repo, pr["number"]) is not None:
            continue
        new.append(pr)
    if max_merged:
        store.write_cursor(repo, max_merged)
    return new
