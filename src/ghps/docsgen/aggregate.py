"""Roll all per-repo records into web/data/projects.json (the L2/L3 feed)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_SUFFIX = ".record.json"


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
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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

    return {"count": len(projects), "skipped": skipped}
