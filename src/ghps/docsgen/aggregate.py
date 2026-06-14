"""Roll all per-repo records into web/data/projects.json (the L2/L3 feed)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ghps.docsgen._util import utc_z

logger = logging.getLogger(__name__)

_SUFFIX = ".record.json"

# Fields kept in the compact index (Tier 1) — enough to scan all repos cheaply
# and decide which full records to fetch, without loading prose/diagrams.
_INDEX_FIELDS = ("slug", "title", "one_liner", "tech", "reuse_tags", "thin", "repo_url")


def compact_entries(projects: list[dict]) -> list[dict]:
    """Project the full records down to the compact index shape (Tier 1)."""
    return [{f: p.get(f) for f in _INDEX_FIELDS} for p in projects]


def write_compact_index(projects: list[dict], output_path: str) -> str:
    """Write the compact index (projects-index.json) and return its path."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": utc_z(),
        "count": len(projects),
        "projects": compact_entries(projects),
    }
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return str(out)


def aggregate_records(records_dir: str, output_path: str) -> dict:
    """Aggregate every ``*.record.json`` in *records_dir* into *output_path*.

    Returns a summary dict ``{"count": int, "skipped": list[str]}``.
    """
    projects: list[dict] = []
    skipped: list[str] = []

    src = Path(records_dir)
    for path in sorted(src.glob(f"*{_SUFFIX}")):
        try:
            projects.append(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("skipping %s: %s", path.name, exc)
            skipped.append(path.name)

    projects.sort(key=lambda p: p.get("slug", ""))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": utc_z(),
        "count": len(projects),
        "projects": projects,
    }
    # Match export.py's JSON convention: keep Unicode (ensure_ascii=False) so
    # repo titles/one-liners stay readable in the live feed, explicit utf-8, and
    # a trailing newline for clean diffs.
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("aggregated %d records to %s", len(projects), output_path)

    return {"count": len(projects), "skipped": skipped, "projects": projects}
