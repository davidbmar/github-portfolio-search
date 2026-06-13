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


def _repo(name):
    return {
        "name": name, "html_url": f"https://github.com/davidbmar/{name}",
        "private": False, "description": "", "language": "Python",
        "topics": [], "stars": 0, "updated_at": "",
    }


def _fake_gh(*names):
    import types

    repos = [_repo(n) for n in (names or ("alpha",))]
    return types.SimpleNamespace(
        fetch_repos=lambda username: repos,
        fetch_readme=lambda o, r: "# Repo\n\nReal content here for the project.",
        fetch_top_files=lambda o, r: [("main.py", "print('hi')")],
        fetch_branches=lambda o, r: [{"name": "main", "commit_sha": "abc1234"}],
        fetch_open_prs=lambda o, r: [],
        compare_commits=lambda o, r, b, h: 0,
    )


class _AlwaysInvalidClient:
    """Returns an LLM payload missing a required field, so every record fails."""

    model = "fake"

    def complete_json(self, system, user):
        bad = dict(_LLM_FIELDS)
        del bad["what_it_is"]
        return bad


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


def test_failed_repo_is_recorded_and_does_not_abort_batch(tmp_path):
    """A repo whose record never validates lands in failed[]; others still run."""
    result = generate.generate_all(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        client=_AlwaysInvalidClient(),
        gh=_fake_gh("alpha", "beta"),
    )
    assert result["generated"] == 0
    assert sorted(result["failed"]) == ["alpha", "beta"]
    # the feed is still rebuilt (empty) even though every repo failed
    feed = json.loads((tmp_path / "web" / "data" / "projects.json").read_text())
    assert feed["count"] == 0


def test_limit_caps_repo_count(tmp_path):
    result = generate.generate_all(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        client=_FakeClient(),
        gh=_fake_gh("alpha", "beta", "gamma"),
        limit=1,
    )
    assert result["generated"] == 1
    assert (tmp_path / "projects" / "alpha.record.json").exists()
    assert not (tmp_path / "projects" / "beta.record.json").exists()
