"""Build the web SPA's client-side search index from docsgen project records.

This is the single source of truth for search: a projection of every project
record into the shape the JS ``SearchEngine.loadSearchIndex`` consumes. Because
it derives from the docsgen corpus (not the GitHub API), private projects such
as ``riff`` are searchable too.

Output entry shape::

    {"repo": <slug>, "title": ..., "one_liner": ...,
     "keywords": [...],                         # tech + reuse_tags, lowercased
     "chunks": [{"source": <field>, "text": ...}]}
"""

from __future__ import annotations

import json
from pathlib import Path

from ghps.docsgen._util import utc_z

# Prose fields contributed as individual searchable chunks, in display order.
_PROSE_FIELDS = ("title", "one_liner", "what_it_is", "how_its_built", "how_to_apply")


def _keywords(project: dict) -> list[str]:
    """Lowercased tech + reuse_tags, de-duplicated, order preserved."""
    out: list[str] = []
    seen: set[str] = set()
    for tag in list(project.get("tech") or []) + list(project.get("reuse_tags") or []):
        term = str(tag).strip().lower()
        if term and term not in seen:
            seen.add(term)
            out.append(term)
    return out


def _chunks(project: dict) -> list[dict]:
    """Build searchable text chunks from a project's prose + features."""
    chunks: list[dict] = []
    for field in _PROSE_FIELDS:
        text = (project.get(field) or "").strip()
        if text:
            chunks.append({"source": field, "text": text})

    features = [str(f).strip() for f in (project.get("features") or []) if str(f).strip()]
    if features:
        chunks.append({"source": "features", "text": " ".join(features)})

    return chunks


def build_search_index(projects: list[dict]) -> list[dict]:
    """Project full records down to search-index entries, keyed by slug.

    Projects without a slug are skipped (nothing to link to).
    """
    entries: list[dict] = []
    for p in projects:
        slug = p.get("slug")
        if not slug:
            continue
        entries.append(
            {
                "repo": slug,
                "title": p.get("title") or slug,
                "one_liner": p.get("one_liner") or "",
                "keywords": _keywords(p),
                "chunks": _chunks(p),
            }
        )
    return entries


def write_search_index(projects: list[dict], output_path: str) -> str:
    """Write projects-search.json and return its path."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    entries = build_search_index(projects)
    payload = {
        "generated_at": utc_z(),
        "count": len(entries),
        "entries": entries,
    }
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return str(out)
