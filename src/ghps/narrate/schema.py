from __future__ import annotations

import hashlib
import json
import re

THEME_STATES = ("candidate", "mature", "published", "archived")

# Scalar fields that must be present AND non-empty.
PR_REQUIRED_NONEMPTY = ("pr_number", "repo", "merged_at", "title", "problem", "approach", "files")
# Fields that must be PRESENT but may legitimately be empty (a PR may change no
# APIs / no tests / have no notable risks). reusable_pattern is a bool (may be False).
PR_REQUIRED_PRESENT = ("components", "apis_changed", "tests_changed", "reusable_pattern", "risks")
# Back-compat union (some callers/tests import PR_REQUIRED).
PR_REQUIRED = PR_REQUIRED_NONEMPTY + PR_REQUIRED_PRESENT
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
    for k in PR_REQUIRED_NONEMPTY:
        if k not in d or d[k] in (None, "", [], {}):
            raise NarrateValidationError(f"missing/empty required field: {k}")
    for k in PR_REQUIRED_PRESENT:
        if k not in d:
            raise NarrateValidationError(f"missing required field: {k}")


def validate_theme_record(d: dict) -> None:
    _require(d, THEME_REQUIRED)
    if d["status"] not in THEME_STATES:
        raise NarrateValidationError(f"bad status: {d['status']}")
