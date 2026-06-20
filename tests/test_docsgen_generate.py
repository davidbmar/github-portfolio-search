"""Orchestrator tests — GitHub + LLM layers faked, filesystem via tmp_path."""

from __future__ import annotations

import json

from ghps.docsgen import generate


_LLM_FIELDS = {
    "title": "Demo", "one_liner": "x", "what_it_is": "x", "how_its_built": "x",
    "how_to_apply": "x", "quickstart": "pip install x", "features": ["f1"],
    "diagram_architecture": "flowchart LR; A-->B",
    "diagram_sequence": "sequenceDiagram; A->>B: hi", "capabilities": [],
    "components": [], "tech": ["python"], "depends_on": [], "integrates_with": [],
    "patterns": [], "reuse_tags": [],
}


class _FakeClient:
    model = "fake"

    def complete_json(self, system, user):
        return dict(_LLM_FIELDS)


def _repo(name, pushed_at=""):
    return {
        "name": name, "html_url": f"https://github.com/davidbmar/{name}",
        "private": False, "description": "", "language": "Python",
        "topics": [], "stars": 0, "updated_at": "", "pushed_at": pushed_at,
    }


def _fake_gh(*names, pushed_at=""):
    import types

    repos = [_repo(n, pushed_at) for n in (names or ("alpha",))]
    return types.SimpleNamespace(
        fetch_repos=lambda username: repos,
        fetch_readme=lambda o, r: "# Repo\n\nReal content here for the project.",
        fetch_top_files=lambda o, r, **kw: [("main.py", "print('hi')")],
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
    # listing page is written and links to the generated page
    index_html = (tmp_path / "web" / "projects" / "index.html").read_text()
    assert 'href="alpha.html"' in index_html
    # progressive-disclosure artifacts: per-repo record, compact index, llms.txt
    assert (tmp_path / "web" / "projects" / "alpha.record.json").exists()
    compact = json.loads((tmp_path / "web" / "data" / "projects-index.json").read_text())
    assert compact["count"] == 1
    assert "one_liner" in compact["projects"][0]
    assert "diagram_architecture" not in compact["projects"][0]  # compact = no prose
    llms = (tmp_path / "web" / "llms.txt").read_text()
    assert "projects-index.json" in llms and "portfolio_find_docs" in llms


def test_publish_all_writes_search_index(tmp_path):
    """The SPA search corpus (projects-search.json) is built from the records."""
    generate.generate_all(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        client=_FakeClient(),
        gh=_fake_gh("alpha"),
    )
    search = json.loads(
        (tmp_path / "web" / "data" / "projects-search.json").read_text()
    )
    assert search["count"] == 1
    entry = search["entries"][0]
    assert entry["repo"] == "alpha"
    assert any(c["source"] == "what_it_is" for c in entry["chunks"])


def test_publish_all_rebuilds_web_from_records_without_llm(tmp_path):
    # First generate one record (LLM), then publish from records alone.
    from ghps.docsgen import generate as gen
    args = _gen_args(tmp_path)
    gen.generate_all(client=_FakeClient(), gh=_fake_gh("alpha"), **args)

    # Remove the rendered HTML, then republish purely from the record on disk.
    (tmp_path / "web" / "projects" / "alpha.html").unlink()
    result = gen.publish_all(
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        base_url="https://example.com",
    )
    assert result["published"] == 1
    assert (tmp_path / "web" / "projects" / "alpha.html").exists()  # re-rendered
    assert (tmp_path / "web" / "projects" / "alpha.record.json").exists()
    assert "https://example.com/data/projects-index.json" in (
        tmp_path / "web" / "llms.txt"
    ).read_text()


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


def _gen_args(tmp_path):
    return dict(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
    )


def test_stale_regenerates_repo_pushed_after_doc(tmp_path):
    args = _gen_args(tmp_path)
    generate.generate_all(client=_FakeClient(), gh=_fake_gh("alpha"), **args)
    # repo pushed far in the future relative to the just-written generated_at
    gh = _fake_gh("alpha", pushed_at="2999-01-01T00:00:00Z")
    result = generate.generate_all(client=_FakeClient(), gh=gh, stale=True, **args)
    assert result["generated"] == 1
    assert result["skipped"] == 0


def test_stale_skips_repo_not_pushed_since_doc(tmp_path):
    args = _gen_args(tmp_path)
    generate.generate_all(client=_FakeClient(), gh=_fake_gh("alpha"), **args)
    # repo last pushed in the distant past → not stale → skipped
    gh = _fake_gh("alpha", pushed_at="2000-01-01T00:00:00Z")
    result = generate.generate_all(client=_FakeClient(), gh=gh, stale=True, **args)
    assert result["generated"] == 0
    assert result["skipped"] == 1


def test_stale_still_generates_missing_repo(tmp_path):
    # no existing record → stale mode still generates it
    result = generate.generate_all(
        client=_FakeClient(), gh=_fake_gh("brandnew", pushed_at=""), stale=True,
        **_gen_args(tmp_path),
    )
    assert result["generated"] == 1


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
