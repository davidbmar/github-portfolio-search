"""Unit tests for repo-hygiene TODO derivation (pure, no network)."""

from __future__ import annotations

from ghps.docsgen import hygiene


def test_clean_repo_has_no_todos():
    todos = hygiene.derive_todos(branch_status=[], open_prs=[])
    assert todos == []


def test_branch_ahead_becomes_todo():
    todos = hygiene.derive_todos(
        branch_status=[{"name": "feat/x", "ahead_by": 3}],
        open_prs=[],
    )
    assert len(todos) == 1
    assert todos[0]["kind"] == "unmerged_branch"
    assert "feat/x" in todos[0]["detail"]
    assert "3" in todos[0]["detail"]


def test_branch_not_ahead_is_ignored():
    todos = hygiene.derive_todos(
        branch_status=[{"name": "stale", "ahead_by": 0}],
        open_prs=[],
    )
    assert todos == []


def test_open_pr_becomes_todo():
    todos = hygiene.derive_todos(
        branch_status=[],
        open_prs=[{"number": 7, "title": "Add feature"}],
    )
    assert len(todos) == 1
    assert todos[0]["kind"] == "open_pr"
    assert "#7" in todos[0]["detail"]
    assert "Add feature" in todos[0]["detail"]


def test_branch_missing_ahead_by_is_ignored():
    todos = hygiene.derive_todos([{"name": "b"}], [])
    assert todos == []


def test_singular_vs_plural_commit_wording():
    one = hygiene.derive_todos([{"name": "b", "ahead_by": 1}], [])
    assert "1 commit ahead" in one[0]["detail"]
    many = hygiene.derive_todos([{"name": "b", "ahead_by": 2}], [])
    assert "2 commits ahead" in many[0]["detail"]
