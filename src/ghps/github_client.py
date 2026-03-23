"""GitHub API client for fetching repo metadata, READMEs, and source files."""

from __future__ import annotations

import base64
import os
from typing import Any

import requests

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
        name, description, language, topics, stars, updated_at, html_url
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


def fetch_top_files(
    owner: str,
    repo: str,
    extensions: tuple[str, ...] | list[str] = DEFAULT_EXTENSIONS,
) -> list[tuple[str, str]]:
    """Fetch source files matching *extensions* from the repo's default branch.

    Uses the Git Trees API with ``recursive=1`` to list all files, then
    fetches the content of matching files via the Blobs API.

    Returns a list of ``(path, content)`` tuples.
    """
    session = _session()
    extensions_set = set(extensions)

    # Get the default branch SHA via the repo endpoint
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

    # Filter to matching blobs
    matching = [
        item
        for item in tree
        if item["type"] == "blob"
        and any(item["path"].endswith(ext) for ext in extensions_set)
    ]

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
