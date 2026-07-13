"""Reuse-aware building — retrieval, provenance, and the reuse ledger.

See ADR-0001. Pure logic; the MCP server wraps these in thin handlers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RELATIONS = frozenset({"reuse", "extend", "link", "inspired", "new"})


def load_building_text(building: str) -> tuple[str, str]:
    """Resolve the tool's `building` arg to (text, source_label).

    A short value that names an existing file is read as a design doc; anything
    else is treated as an inline description. The 400-char guard stops a long
    design-doc-passed-as-text from being probed as a filesystem path.
    """
    try:
        if len(building) < 400 and Path(building).is_file():
            return Path(building).read_text(), f"doc: {building}"
    except OSError:
        pass
    return building, f"description: {building[:80]}"


def record_reuse(
    ledger_path: str,
    built: str,
    reused: list[str],
    relation: str,
    note: str = "",
    session: str = "",
    ts: str | None = None,
) -> dict:
    """Append one reuse decision to the JSONL ledger; return the written record."""
    if not built:
        raise ValueError("built is required")
    if relation not in RELATIONS:
        raise ValueError(f"relation must be one of {sorted(RELATIONS)}, got {relation!r}")

    record = {
        "ts": ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "built": built,
        "reused": list(reused or []),
        "relation": relation,
        "note": note,
        "session": session,
    }
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")
    return record
