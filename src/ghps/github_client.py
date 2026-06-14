"""GitHub API client for fetching repo metadata, READMEs, and source files."""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"
PER_PAGE = 100

DEFAULT_EXTENSIONS = (".py", ".js", ".ts", ".go", ".rs", ".java")


def _session() -> requests.Session:
    """Return a requests session with auth header if GITHUB_TOKEN is set."""
    s = requests.Session()
    s.headers["Accept"] = "application/vnd.github+json"
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


def fetch_repos(username: str) -> list[dict[str, Any]]:
    """Fetch all repos for *username*, handling pagination.

    Uses /user/repos (authenticated, includes private) when a token is set,
    falls back to /users/{username}/repos (public only) otherwise.

    Returns a list of dicts with keys:
        name, description, language, topics, stars, updated_at, pushed_at,
        html_url, private
    """
    session = _session()
    repos: list[dict[str, Any]] = []
    page = 1
    has_token = "Authorization" in session.headers

    while True:
        if has_token:
            resp = session.get(
                f"{API_BASE}/user/repos",
                params={"per_page": PER_PAGE, "page": page, "affiliation": "owner"},
            )
        else:
            resp = session.get(
                f"{API_BASE}/users/{username}/repos",
                params={"per_page": PER_PAGE, "page": page, "type": "owner"},
            )
        resp.raise_for_status()
        data = resp.json()

        for r in data:
            repos.append(
                {
                    "name": r["name"],
                    "description": r.get("description") or "",
                    "language": r.get("language") or "",
                    "topics": r.get("topics", []),
                    "stars": r.get("stargazers_count", 0),
                    "updated_at": r.get("updated_at", ""),
                    "pushed_at": r.get("pushed_at", ""),
                    "default_branch": r.get("default_branch", ""),
                    "html_url": r.get("html_url", ""),
                    "private": r.get("private", False),
                }
            )

        if len(data) < PER_PAGE:
            break
        page += 1

    return repos


def fetch_readme(owner: str, repo: str) -> str:
    """Fetch the README content for *owner/repo*.

    Returns the decoded text, or an empty string if no README exists.
    """
    session = _session()
    resp = session.get(f"{API_BASE}/repos/{owner}/{repo}/readme")

    if resp.status_code == 404:
        return ""
    resp.raise_for_status()

    data = resp.json()
    content = data.get("content", "")
    encoding = data.get("encoding", "base64")

    if encoding == "base64" and content:
        return base64.b64decode(content).decode("utf-8", errors="replace")
    return content


def fetch_portfolio_json(owner: str, repo: str) -> dict | None:
    """Fetch and parse portfolio.json from a repo's root.

    Calls the GitHub Contents API for portfolio.json. Returns the parsed
    dict if the file exists and is valid JSON, or None otherwise.
    """
    session = _session()
    resp = session.get(f"{API_BASE}/repos/{owner}/{repo}/contents/portfolio.json")

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        logger.warning("Unexpected status %d fetching portfolio.json for %s/%s", resp.status_code, owner, repo)
        return None

    try:
        data = resp.json()
        content = data.get("content", "")
        encoding = data.get("encoding", "base64")

        if encoding == "base64" and content:
            raw = base64.b64decode(content).decode("utf-8", errors="replace")
        else:
            raw = content

        return json.loads(raw)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse portfolio.json for %s/%s: %s", owner, repo, exc)
        return None


def fetch_top_files(
    owner: str,
    repo: str,
    extensions: tuple[str, ...] | list[str] = DEFAULT_EXTENSIONS,
    *,
    default_branch: str | None = None,
    max_files: int | None = None,
) -> list[tuple[str, str]]:
    """Fetch source files matching *extensions* from the repo's default branch.

    Uses the Git Trees API with ``recursive=1`` to list all files, then fetches
    the content of matching files via the Blobs API.

    Pass *default_branch* to skip the extra repo lookup when the caller already
    knows it. Pass *max_files* to cap how many blobs are downloaded — callers
    that only use the first few files (e.g. doc generation) avoid hundreds of
    wasted Blob API calls on large repos.

    Returns a list of ``(path, content)`` tuples.
    """
    session = _session()
    extensions_set = set(extensions)

    # Resolve the default branch — only hit the repo endpoint if not supplied.
    if not default_branch:
        repo_resp = session.get(f"{API_BASE}/repos/{owner}/{repo}")
        if repo_resp.status_code == 404:
            return []
        repo_resp.raise_for_status()
        default_branch = repo_resp.json().get("default_branch", "main")

    # Fetch full tree
    tree_resp = session.get(
        f"{API_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}",
        params={"recursive": "1"},
    )
    if tree_resp.status_code == 404:
        return []
    tree_resp.raise_for_status()

    tree = tree_resp.json().get("tree", [])

    # Filter to matching blobs, then cap BEFORE downloading their content.
    matching = [
        item
        for item in tree
        if item["type"] == "blob"
        and any(item["path"].endswith(ext) for ext in extensions_set)
    ]
    if max_files is not None:
        matching = matching[:max_files]

    results: list[tuple[str, str]] = []
    for item in matching:
        blob_resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/git/blobs/{item['sha']}"
        )
        if blob_resp.status_code != 200:
            continue
        blob = blob_resp.json()
        content = blob.get("content", "")
        if blob.get("encoding") == "base64" and content:
            content = base64.b64decode(content).decode("utf-8", errors="replace")
        results.append((item["path"], content))

    return results


def fetch_branches(owner: str, repo: str) -> list[dict[str, str]]:
    """List branches for *owner/repo*.

    Returns a list of ``{"name": str, "commit_sha": str}``. Empty list if the
    repo is missing. Handles pagination.
    """
    session = _session()
    branches: list[dict[str, str]] = []
    page = 1

    while True:
        resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/branches",
            params={"per_page": PER_PAGE, "page": page},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()

        for b in data:
            branches.append(
                {"name": b["name"], "commit_sha": b.get("commit", {}).get("sha", "")}
            )

        if len(data) < PER_PAGE:
            break
        page += 1

    return branches


def compare_commits(owner: str, repo: str, base: str, head: str) -> int:
    """Return how many commits *head* is ahead of *base* (0 if unknown)."""
    session = _session()
    resp = session.get(f"{API_BASE}/repos/{owner}/{repo}/compare/{base}...{head}")
    if resp.status_code != 200:
        if resp.status_code != 404:
            logger.debug(
                "compare %s/%s %s...%s returned %d; treating as 0 ahead",
                owner, repo, base, head, resp.status_code,
            )
        return 0
    return int(resp.json().get("ahead_by", 0))


def fetch_open_prs(owner: str, repo: str) -> list[dict[str, Any]]:
    """List open pull requests for *owner/repo*.

    Returns a list of ``{"number": int, "title": str}``. Empty list if none or
    if the repo is missing. Handles pagination.
    """
    session = _session()
    prs: list[dict[str, Any]] = []
    page = 1

    while True:
        resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/pulls",
            params={"state": "open", "per_page": PER_PAGE, "page": page},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()

        for pr in data:
            prs.append({"number": pr["number"], "title": pr.get("title", "")})

        if len(data) < PER_PAGE:
            break
        page += 1

    return prs
