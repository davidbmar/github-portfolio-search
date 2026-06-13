"""Assemble everything a single repo's doc generation needs.

Pulls README, key source, branch/PR state from the GitHub layer (injectable for
tests), decides the ``thin`` flag, and computes ``branch_status`` by comparing
only NON-default branches against the default branch (bounds API cost).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ghps import github_client as _default_gh

# Treat a repo as "thin" when there is essentially nothing to document.
_THIN_README_CHARS = 80


@dataclass
class RepoContext:
    slug: str
    owner: str
    repo_url: str
    visibility: str  # "public" | "private"
    default_branch: str
    head_sha: str
    description: str
    language: str
    topics: list[str]
    readme: str
    source_files: list[tuple[str, str]]
    branch_status: list[dict] = field(default_factory=list)  # non-default branches
    open_prs: list[dict] = field(default_factory=list)
    thin: bool = False


def build_context(repo_meta: dict, *, owner: str, gh=_default_gh) -> RepoContext:
    """Build a :class:`RepoContext` for one repo.

    Args:
        repo_meta: a dict from ``github_client.fetch_repos`` (name, description,
            language, topics, html_url, private, ...).
        owner: the GitHub owner/org (e.g. "davidbmar").
        gh: the github_client module (injectable for tests).
    """
    name = repo_meta["name"]
    readme = gh.fetch_readme(owner, name)
    source_files = gh.fetch_top_files(owner, name)
    branches = gh.fetch_branches(owner, name)
    open_prs = gh.fetch_open_prs(owner, name)

    # The default branch is the one whose name is "main" or "master"; fall back
    # to the first branch. (We avoid a separate repo call: branches + heuristic.)
    branch_names = [b["name"] for b in branches]
    default_branch = "main"
    if "main" not in branch_names:
        default_branch = "master" if "master" in branch_names else (
            branch_names[0] if branch_names else "main"
        )

    head_sha = ""
    for b in branches:
        if b["name"] == default_branch:
            head_sha = b["commit_sha"]
            break

    branch_status: list[dict] = []
    for b in branches:
        if b["name"] == default_branch:
            continue
        ahead = gh.compare_commits(owner, name, default_branch, b["name"])
        branch_status.append({"name": b["name"], "ahead_by": ahead})

    thin = (
        len((readme or "").strip()) < _THIN_README_CHARS and not source_files
    )

    return RepoContext(
        slug=name,
        owner=owner,
        repo_url=repo_meta.get("html_url", f"https://github.com/{owner}/{name}"),
        visibility="private" if repo_meta.get("private") else "public",
        default_branch=default_branch,
        head_sha=head_sha,
        description=repo_meta.get("description", ""),
        language=repo_meta.get("language", ""),
        topics=list(repo_meta.get("topics", [])),
        readme=readme or "",
        source_files=source_files,
        branch_status=branch_status,
        open_prs=open_prs,
        thin=thin,
    )
