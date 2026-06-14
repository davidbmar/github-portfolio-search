"""Assemble everything a single repo's doc generation needs.

Pulls README, key source, branch/PR state from the GitHub layer (injectable for
tests), decides the ``thin`` flag, and computes ``branch_status`` by comparing
only NON-default branches against the default branch (bounds API cost).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ghps import github_client as _default_gh

# Treat a repo as "thin" when there is essentially nothing to document.
_THIN_README_CHARS = 80

# How many source files to fetch for the prompt (record_gen uses the first 6;
# fetch a small buffer). Bounds Blob API calls on large repos.
_MAX_SOURCE_FILES = 8


def _pick_default_branch(branch_names: list[str]) -> str:
    """Heuristic default branch: main → master → first → 'main'."""
    if "main" in branch_names:
        return "main"
    if "master" in branch_names:
        return "master"
    return branch_names[0] if branch_names else "main"

# Markdown image:  ![alt](url)   and HTML <img src="url">
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)")
_HTML_IMAGE = re.compile(r"""<img[^>]+src\s*=\s*["']([^"']+)""", re.IGNORECASE)

# Substrings that mark an image as a badge/CI shield rather than a UI screenshot.
# Use slash-delimited "/badge/" (not bare "badge") so a real screenshot path like
# docs/badge-system-screenshot.png is not mistaken for a shield.
_BADGE_MARKERS = (
    "shields.io",
    "/badge/",
    "badge.svg",
    "badge.fury.io",
    "/workflows/",
    "travis-ci",
    "circleci",
    "codecov",
    "coveralls",
    "app.netlify.com",
    "/actions/workflow",
)


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
    screenshot_url: str = ""  # first non-badge README image (absolute URL), or ""


def first_readme_image(readme: str, owner: str, repo: str, branch: str) -> str:
    """Return an absolute URL for the first non-badge image in *readme*, or "".

    Markdown (``![](...)``) and HTML (``<img src=...>``) images are considered in
    document order. Badge/CI-shield images are skipped. Relative paths are
    resolved against raw.githubusercontent.com for the repo's default branch so
    the image loads on the published page (which is NOT on github.com).
    """
    if not readme:
        return ""

    candidates: list[tuple[int, str]] = []
    for pattern in (_MD_IMAGE, _HTML_IMAGE):
        for m in pattern.finditer(readme):
            candidates.append((m.start(), m.group(1).strip()))
    candidates.sort(key=lambda c: c[0])

    for _pos, url in candidates:
        low = url.lower()
        if low.startswith("data:"):  # inline base64 image — can't resolve to a URL
            continue
        if any(marker in low for marker in _BADGE_MARKERS):
            continue
        if url.startswith(("http://", "https://")):
            return url
        if url.startswith("//"):
            return "https:" + url
        # Relative path → resolve to the raw content host. Strip a single leading
        # "./" then any leading "/", being careful not to eat a dotfile dir name.
        rel = url[2:] if url.startswith("./") else url
        rel = rel.lstrip("/")
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rel}"

    return ""


def build_context(repo_meta: dict, *, owner: str, gh=_default_gh) -> RepoContext:
    """Build a :class:`RepoContext` for one repo.

    Args:
        repo_meta: a dict from ``github_client.fetch_repos`` (name, description,
            language, topics, html_url, private, ...).
        owner: the GitHub owner/org (e.g. "davidbmar").
        gh: the github_client module (injectable for tests).
    """
    name = repo_meta["name"]
    branches = gh.fetch_branches(owner, name)
    branch_names = [b["name"] for b in branches]

    # Prefer the authoritative default branch from the repo metadata; fall back
    # to a name heuristic (main → master → first) when it's absent.
    default_branch = repo_meta.get("default_branch") or _pick_default_branch(branch_names)

    readme = gh.fetch_readme(owner, name)
    # Pass default_branch (skips a redundant repo API call) and cap the blob
    # downloads — doc generation only consumes the first few files.
    source_files = gh.fetch_top_files(
        owner, name, default_branch=default_branch, max_files=_MAX_SOURCE_FILES
    )
    open_prs = gh.fetch_open_prs(owner, name)

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

    screenshot_url = first_readme_image(readme or "", owner, name, default_branch)

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
        screenshot_url=screenshot_url,
    )
