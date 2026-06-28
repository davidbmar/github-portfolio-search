"""Stable Learn-page slugs across cold rebuilds.

The narrate state dir (``web/data/narrate/``) is not committed, so every CI or
local run is a cold rebuild that re-clusters PRs and re-mints theme titles via
the LLM. Titles drift, so slugs drift, and a drifted slug deployed with
``s3 sync --delete`` would 404 any link that points at the old URL (e.g. the
/daily feed).

This module pins slugs to a *committed* registry keyed by a theme's set of PR
numbers — the part of a theme that is stable across rebuilds. Matching is by
Jaccard overlap so a theme that later gains a PR still maps to its original
slug. Pure functions only; the two I/O helpers are thin JSON wrappers.
"""

from __future__ import annotations

import json
from pathlib import Path

MATCH_THRESHOLD = 0.5


def _jaccard(a, b) -> float:
    sa, sb = set(a or []), set(b or [])
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


def match_slug(pr_numbers, registry, *, threshold: float = MATCH_THRESHOLD) -> str | None:
    """Return the registered slug whose PR set best overlaps ``pr_numbers``.

    Ties break on slug name so the result is deterministic. Returns ``None`` when
    the best overlap is below ``threshold`` (a genuinely new theme).
    """
    best_slug, best_score = None, 0.0
    for entry in registry:
        score = _jaccard(pr_numbers, entry.get("pr_numbers", []))
        slug = entry.get("slug", "")
        if score > best_score or (score == best_score and best_slug is not None and slug < best_slug):
            best_slug, best_score = slug, score
    return best_slug if best_score >= threshold else None


def reconcile_slugs(themes, registry, *, threshold: float = MATCH_THRESHOLD):
    """Pin each theme's slug to the registry entry it matches. Mutates ``themes``.

    Themes are matched in a deterministic order (by minimum PR key) so that when
    two themes both overlap one entry, the same theme wins each run. A pinned
    slug is never assigned to two themes in one run — the loser keeps its minted
    slug to avoid duplicate URLs.
    """
    used: set[str] = set()
    ordered = sorted(themes, key=lambda t: min(t.get("pr_numbers", []) or [""]))
    for theme in ordered:
        pinned = match_slug(theme.get("pr_numbers", []), registry, threshold=threshold)
        if pinned and pinned not in used:
            theme["slug"] = pinned
        used.add(theme.get("slug"))
    return themes


def update_registry(registry, published_themes):
    """Return a registry that includes every published theme.

    Existing entries (matched by slug) have their PR set and repos unioned with
    the latest membership; genuinely new themes are appended.
    """
    by_slug = {e["slug"]: dict(e) for e in registry}
    for theme in published_themes:
        slug = theme["slug"]
        entry = by_slug.get(slug, {"slug": slug})
        entry["title"] = theme.get("title", entry.get("title", ""))
        entry["repos"] = sorted(set(entry.get("repos", [])) | set(theme.get("repos", [])))
        entry["pr_numbers"] = sorted(set(entry.get("pr_numbers", [])) | set(theme.get("pr_numbers", [])))
        by_slug[slug] = entry
    return list(by_slug.values())


def load_registry(path) -> list:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text())
    return data if isinstance(data, list) else []


def save_registry(path, registry) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(registry, key=lambda e: e.get("slug", ""))
    p.write_text(json.dumps(ordered, indent=2, sort_keys=True), encoding="utf-8")
