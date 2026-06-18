"""Unit tests for aggregating per-repo records into the machine feed."""

from __future__ import annotations

import json

from ghps.docsgen import aggregate


def _write_record(dir_path, slug, **overrides):
    rec = {"slug": slug, "title": slug.title(), "thin": False}
    rec.update(overrides)
    (dir_path / f"{slug}.record.json").write_text(json.dumps(rec))
    return rec


def test_aggregates_all_records_sorted_by_slug(tmp_path):
    records_dir = tmp_path / "projects"
    records_dir.mkdir()
    _write_record(records_dir, "zebra")
    _write_record(records_dir, "alpha")
    out = tmp_path / "web" / "data" / "projects.json"

    result = aggregate.aggregate_records(str(records_dir), str(out))

    assert out.exists()
    data = json.loads(out.read_text())
    assert [p["slug"] for p in data["projects"]] == ["alpha", "zebra"]
    assert data["count"] == 2
    assert result["count"] == 2


def test_ignores_non_record_files(tmp_path):
    records_dir = tmp_path / "projects"
    records_dir.mkdir()
    _write_record(records_dir, "alpha")
    (records_dir / "README.md").write_text("not a record")
    out = tmp_path / "projects.json"

    aggregate.aggregate_records(str(records_dir), str(out))
    data = json.loads(out.read_text())
    assert data["count"] == 1


def test_skips_malformed_json(tmp_path):
    records_dir = tmp_path / "projects"
    records_dir.mkdir()
    _write_record(records_dir, "good")
    (records_dir / "broken.record.json").write_text("{not json")
    out = tmp_path / "projects.json"

    result = aggregate.aggregate_records(str(records_dir), str(out))
    assert result["count"] == 1
    assert result["skipped"] == ["broken.record.json"]


def test_compact_entries_keeps_only_index_fields():
    full = {
        "slug": "x", "title": "X", "one_liner": "o", "tech": ["py"],
        "reuse_tags": ["t"], "thin": False, "repo_url": "u",
        "pushed_at": "2026-06-14T00:00:00Z",
        "what_it_is": "long prose", "diagram_architecture": "flowchart",
    }
    entry = aggregate.compact_entries([full])[0]
    assert set(entry) == {
        "slug", "title", "one_liner", "tech", "reuse_tags", "thin", "repo_url",
        "pushed_at",
    }
    assert "what_it_is" not in entry and "diagram_architecture" not in entry


def test_compact_entries_includes_pushed_at_for_recency():
    """pushed_at rides along in the compact index so 'latest' views can sort."""
    entry = aggregate.compact_entries(
        [{"slug": "x", "pushed_at": "2026-06-14T00:00:00Z"}]
    )[0]
    assert entry["pushed_at"] == "2026-06-14T00:00:00Z"


def test_write_compact_index(tmp_path):
    out = tmp_path / "data" / "projects-index.json"
    aggregate.write_compact_index([{"slug": "a", "one_liner": "hi"}], str(out))
    data = json.loads(out.read_text())
    assert data["count"] == 1 and data["projects"][0]["slug"] == "a"


def test_empty_directory_yields_zero_count(tmp_path):
    records_dir = tmp_path / "projects"
    records_dir.mkdir()
    out = tmp_path / "projects.json"

    result = aggregate.aggregate_records(str(records_dir), str(out))
    assert result["count"] == 0
    assert result["skipped"] == []
    assert result["projects"] == []
    assert json.loads(out.read_text())["projects"] == []
