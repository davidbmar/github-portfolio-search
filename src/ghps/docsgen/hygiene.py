"""Derive the repo-hygiene TODO list from GitHub branch/PR state.

Pure function over already-fetched data — no network here. The GitHub API sees
branches and open PRs but NOT local uncommitted state, so local dirtiness is
deliberately out of scope for v1.
"""

from __future__ import annotations


def derive_todos(branch_status: list[dict], open_prs: list[dict]) -> list[dict]:
    """Build the ``todos[]`` block from branch and PR state.

    Args:
        branch_status: list of ``{"name": str, "ahead_by": int}`` for every
            non-default branch (ahead_by = commits ahead of the default branch).
        open_prs: list of ``{"number": int, "title": str}``.

    Returns a list of ``{"kind": str, "detail": str}`` dicts.
    """
    todos: list[dict] = []

    for branch in branch_status:
        ahead = branch.get("ahead_by", 0)
        if ahead and ahead > 0:
            noun = "commit" if ahead == 1 else "commits"
            todos.append(
                {
                    "kind": "unmerged_branch",
                    "detail": f"{branch['name']} is {ahead} {noun} ahead of the default branch",
                }
            )

    for pr in open_prs:
        todos.append(
            {
                "kind": "open_pr",
                "detail": f"PR #{pr['number']}: {pr['title']}",
            }
        )

    return todos
