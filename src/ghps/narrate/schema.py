from __future__ import annotations

import hashlib
import json
import re

THEME_STATES = ("candidate", "mature", "published", "archived")

PR_REQUIRED = (
    "pr_number", "repo", "merged_at", "title",
    "problem", "approach", "components", "apis_changed",
    "tests_changed", "reusable_pattern", "risks", "files",
)
THEME_REQUIRED = (
    "theme_id", "slug", "title", "status", "repos", "pr_numbers",
    "summary", "narrative",
)


class NarrateValidationError(RuntimeError):
    """Raised when a PRRecord or ThemeRecord fails validation."""


def files_hash(files: list[dict]) -> str:
    norm = sorted(
        (f.get("path", ""), f.get("status", ""), int(f.get("adds", 0)), int(f.get("dels", 0)))
        for f in files
    )
    blob = json.dumps(norm, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def make_slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return re.sub(r"-+", "-", s).strip("-")


def _require(d: dict, keys: tuple[str, ...]) -> None:
    for k in keys:
        if k not in d or d[k] in (None, "", [], {}):
            raise NarrateValidationError(f"missing/empty required field: {k}")


def validate_pr_record(d: dict) -> None:
    _require(d, PR_REQUIRED)


def validate_theme_record(d: dict) -> None:
    _require(d, THEME_REQUIRED)
    if d["status"] not in THEME_STATES:
        raise NarrateValidationError(f"bad status: {d['status']}")
