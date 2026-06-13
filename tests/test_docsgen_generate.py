"""Orchestrator tests — GitHub + LLM layers faked, filesystem via tmp_path."""

from __future__ import annotations

import json

from ghps.docsgen import generate


_LLM_FIELDS = {
    "title": "Demo", "one_liner": "x", "what_it_is": "x", "how_its_built": "x",
    "how_to_apply": "x", "diagram_architecture": "flowchart LR; A-->B",
    "diagram_sequence": "sequenceDiagram; A->>B: hi", "capabilities": [],
    "components": [], "tech": ["python"], "depends_on": [], "integrates_with": [],
    "patterns": [], "reuse_tags": [],
}


class _FakeClient:
    model = "fake"

    def complete_json(self, system, user):
        return dict(_LLM_FIELDS)


def _fake_gh():
    import types

    def fetch_repos(username):
        return [
            {"name": "alpha", "html_url": "https://github.com/davidbmar/alpha",
             "private": False, "description": "", "language": "Python",
             "topics": [], "stars": 0, "updated_at": ""},
        ]

    m = types.SimpleNamespace(
        fetch_repos=fetch_repos,
        fetch_readme=lambda o, r: "# Alpha\n\nReal content here for the project.",
        fetch_top_files=lambda o, r: [("main.py", "print('hi')")],
        fetch_branches=lambda o, r: [{"name": "main", "commit_sha": "abc1234"}],
        fetch_open_prs=lambda o, r: [],
        compare_commits=lambda o, r, b, h: 0,
    )
    return m


def test_generate_all_writes_record_html_and_aggregate(tmp_path):
    result = generate.generate_all(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        client=_FakeClient(),
        gh=_fake_gh(),
    )
    assert result["generated"] == 1
    assert (tmp_path / "projects" / "alpha.record.json").exists()
    assert (tmp_path / "web" / "projects" / "alpha.html").exists()
    feed = json.loads((tmp_path / "web" / "data" / "projects.json").read_text())
    assert feed["count"] == 1


def test_idempotent_skips_existing_unless_force(tmp_path):
    args = dict(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        gh=_fake_gh(),
    )
    generate.generate_all(client=_FakeClient(), **args)
    second = generate.generate_all(client=_FakeClient(), **args)
    assert second["generated"] == 0
    assert second["skipped"] == 1
    forced = generate.generate_all(client=_FakeClient(), force=True, **args)
    assert forced["generated"] == 1


def test_only_filters_to_one_slug(tmp_path):
    result = generate.generate_all(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        client=_FakeClient(),
        gh=_fake_gh(),
        only="nonexistent",
    )
    assert result["generated"] == 0
