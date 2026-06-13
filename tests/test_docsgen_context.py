"""Unit tests for per-repo context assembly (GitHub layer mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ghps.docsgen import context


def _repo_meta(**overrides):
    base = {
        "name": "demo",
        "description": "A demo repo",
        "language": "Python",
        "topics": ["demo"],
        "stars": 1,
        "updated_at": "2025-01-01T00:00:00Z",
        "html_url": "https://github.com/davidbmar/demo",
        "private": False,
    }
    base.update(overrides)
    return base


def _fake_gh(*, readme="# Demo", files=None, branches=None, prs=None, ahead=0):
    gh = MagicMock()
    gh.fetch_readme.return_value = readme
    gh.fetch_top_files.return_value = (
        [("main.py", "print('hi')")] if files is None else files
    )
    gh.fetch_branches.return_value = branches or [
        {"name": "main", "commit_sha": "aaa111"}
    ]
    gh.fetch_open_prs.return_value = prs or []
    gh.compare_commits.return_value = ahead
    return gh


def test_builds_context_with_slug_and_owner():
    gh = _fake_gh()
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    assert ctx.slug == "demo"
    assert ctx.owner == "davidbmar"
    assert ctx.head_sha == "aaa111"
    assert ctx.visibility == "public"


def test_default_branch_excluded_from_branch_status():
    gh = _fake_gh(
        branches=[
            {"name": "main", "commit_sha": "aaa"},
            {"name": "feat/x", "commit_sha": "bbb"},
        ],
        ahead=2,
    )
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    names = [b["name"] for b in ctx.branch_status]
    assert "main" not in names
    assert names == ["feat/x"]
    assert ctx.branch_status[0]["ahead_by"] == 2
    # compare_commits called once (only the non-default branch)
    assert gh.compare_commits.call_count == 1


def test_thin_when_readme_empty_and_no_source():
    gh = _fake_gh(readme="", files=[])
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    assert ctx.thin is True


def test_not_thin_with_real_readme():
    gh = _fake_gh(readme="# Demo\n\nA real project with content.")
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    assert ctx.thin is False


def test_private_visibility_propagates():
    gh = _fake_gh()
    ctx = context.build_context(_repo_meta(private=True), owner="davidbmar", gh=gh)
    assert ctx.visibility == "private"
