"""Schema definition + validator for the L0 structured record.

The record is the single source of truth: the renderer draws a page from it
and the aggregator feeds it to L2/L3. Validation is hand-rolled (no jsonschema
dependency) and returns a list of human-readable error strings — an empty list
means the record is valid.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "v1"

# Prose / scalar string fields that must be present and of type str. Empty
# strings are intentionally tolerated: provenance fields like source_commit are
# legitimately "" for thin repos with no resolvable HEAD (see record_gen).
REQUIRED_STRING_FIELDS = (
    "slug",
    "title",
    "repo_url",
    "one_liner",
    "what_it_is",
    "how_its_built",
    "how_to_apply",
    "diagram_architecture",
    "diagram_sequence",
    "generated_at",
    "source_commit",
    "model",
)

# List-of-string metadata fields (may be empty lists, but must be lists).
REQUIRED_LIST_FIELDS = (
    "capabilities",
    "components",
    "tech",
    "depends_on",
    "integrates_with",
    "patterns",
    "reuse_tags",
)

ENUMS = {
    "visibility": ("public", "private"),
    "status": ("idea", "building", "shipped"),
}


def validate_record(record: Any) -> list[str]:
    """Return a list of validation errors for *record* (empty list = valid)."""
    errors: list[str] = []

    if not isinstance(record, dict):
        return [f"record must be a dict, got {type(record).__name__}"]

    for field in REQUIRED_STRING_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")
        elif not isinstance(record[field], str):
            errors.append(f"field {field} must be a string")

    for field in REQUIRED_LIST_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")
        elif not isinstance(record[field], list):
            errors.append(f"field {field} must be a list")
        elif not all(isinstance(x, str) for x in record[field]):
            errors.append(f"field {field} must contain only strings")

    for field, allowed in ENUMS.items():
        if field not in record:
            errors.append(f"missing required field: {field}")
        elif record[field] not in allowed:
            errors.append(
                f"field {field} must be one of {allowed}, got {record.get(field)!r}"
            )

    if "thin" not in record:
        errors.append("missing required field: thin")
    elif not isinstance(record["thin"], bool):
        errors.append("field thin must be a boolean")

    if "todos" not in record:
        errors.append("missing required field: todos")
    elif not isinstance(record["todos"], list):
        errors.append("field todos must be a list")

    return errors
