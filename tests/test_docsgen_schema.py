"""Unit tests for the L0 record schema validator."""

from __future__ import annotations

from ghps.docsgen import schema


def _valid_record() -> dict:
    return {
        "slug": "demo",
        "title": "Demo Project",
        "repo_url": "https://github.com/user/demo",
        "visibility": "public",
        "status": "shipped",
        "thin": False,
        "one_liner": "A demo.",
        "what_it_is": "It is a demo.",
        "how_its_built": "With Python.",
        "how_to_apply": "Copy the pattern.",
        "diagram_architecture": "flowchart LR; A-->B",
        "diagram_sequence": "sequenceDiagram; A->>B: hi",
        "capabilities": ["demoing"],
        "components": ["thing"],
        "tech": ["python"],
        "depends_on": ["requests"],
        "integrates_with": [],
        "patterns": ["adapter"],
        "reuse_tags": ["demo-tag"],
        "todos": [],
        "generated_at": "2026-06-13T00:00:00Z",
        "source_commit": "abc1234",
        "model": "qwen-plus",
    }


def test_valid_record_has_no_errors():
    assert schema.validate_record(_valid_record()) == []


def test_missing_required_string_is_reported():
    rec = _valid_record()
    del rec["what_it_is"]
    errors = schema.validate_record(rec)
    assert any("what_it_is" in e for e in errors)


def test_wrong_type_for_list_field_is_reported():
    rec = _valid_record()
    rec["capabilities"] = "not a list"
    errors = schema.validate_record(rec)
    assert any("capabilities" in e for e in errors)


def test_bad_enum_value_is_reported():
    rec = _valid_record()
    rec["status"] = "launched"  # not in idea|building|shipped
    errors = schema.validate_record(rec)
    assert any("status" in e for e in errors)


def test_thin_must_be_bool():
    rec = _valid_record()
    rec["thin"] = "yes"
    errors = schema.validate_record(rec)
    assert any("thin" in e for e in errors)
