"""Small shared helpers for the docsgen package."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_z() -> str:
    """Current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
