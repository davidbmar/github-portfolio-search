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
    if tree_resp.status_code in (404, 409):  # missing branch / empty repo
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


DOCS_HTML_PREFIX = "docs/html/"
DOCS_MD_PREFIX = "docs/md/"
# Binary web assets republished alongside docs/html/ pages (images/css/js/fonts).
DOC_ASSET_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".avif",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".otf",
)
_MAX_ASSET_BYTES = 15 * 1024 * 1024  # skip a single asset larger than 15 MB


def _fetch_docs_under(
    owner: str,
    repo: str,
    prefix: str,
    suffix,
    *,
    default_branch: str | None,
    max_files: int,
    decode: bool = True,
    max_bytes: int | None = None,
):
    """Fetch every ``<prefix>**/*<suffix>`` blob from the repo's default branch.

    Shared engine for :func:`fetch_html_docs`, :func:`fetch_markdown_docs`, and
    :func:`fetch_html_doc_assets`. *suffix* may be a string or a tuple of
    extensions. With ``decode=True`` returns ``(path, str)`` (text docs); with
    ``decode=False`` returns ``(path, bytes)`` (binary assets). *max_bytes* skips
    oversized blobs. The explicit ``docs/html/`` / ``docs/md/`` folder avoids
    publishing generated output elsewhere under ``docs/``.
    """
    session = _session()

    if not default_branch:
        repo_resp = session.get(f"{API_BASE}/repos/{owner}/{repo}")
        if repo_resp.status_code == 404:
            return []
        repo_resp.raise_for_status()
        default_branch = repo_resp.json().get("default_branch", "main")

    tree_resp = session.get(
        f"{API_BASE}/repos/{owner}/{repo}/git/trees/{default_branch}",
        params={"recursive": "1"},
    )
    if tree_resp.status_code in (404, 409):  # missing branch / empty repo
        return []
    tree_resp.raise_for_status()
    tree = tree_resp.json().get("tree", [])

    matching = [
        item
        for item in tree
        if item.get("type") == "blob"
        and item["path"].startswith(prefix)
        and item["path"].lower().endswith(suffix)
        and (max_bytes is None or item.get("size", 0) <= max_bytes)
    ][:max_files]

    results: list = []
    for item in matching:
        blob_resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/git/blobs/{item['sha']}"
        )
        if blob_resp.status_code != 200:
            continue
        blob = blob_resp.json()
        content = blob.get("content", "")
        if blob.get("encoding") == "base64" and content:
            raw = base64.b64decode(content)
            content = raw.decode("utf-8", errors="replace") if decode else raw
        elif not decode:
            content = content.encode()  # rare: non-base64 blob, normalize to bytes
        results.append((item["path"], content))

    return results


def fetch_html_doc_assets(
    owner: str,
    repo: str,
    *,
    default_branch: str | None = None,
    max_files: int = 250,
) -> list[tuple[str, bytes]]:
    """Fetch binary web assets (images/css/js/fonts) under ``docs/html/``.

    Returns ``(path, bytes)`` so they can be republished verbatim alongside the
    HTML docs. Oversized assets (> 15 MB) are skipped.
    """
    return _fetch_docs_under(
        owner, repo, DOCS_HTML_PREFIX, DOC_ASSET_SUFFIXES,
        default_branch=default_branch, max_files=max_files,
        decode=False, max_bytes=_MAX_ASSET_BYTES,
    )


def fetch_html_docs(
    owner: str,
    repo: str,
    *,
    default_branch: str | None = None,
    max_files: int = 250,
) -> list[tuple[str, str]]:
    """Fetch every ``docs/html/**/*.html`` file from the repo's default branch.

    Convention: a project opts a page into its portfolio docs by committing it
    under ``docs/html/``. Those pages are republished alongside the generated
    project page (see ``generate.publish_all``). Returns ``(path, content)``
    tuples (e.g. ``docs/html/roadmap.html``). Empty if missing.
    """
    return _fetch_docs_under(
        owner, repo, DOCS_HTML_PREFIX, ".html",
        default_branch=default_branch, max_files=max_files,
    )


def fetch_markdown_docs(
    owner: str,
    repo: str,
    *,
    default_branch: str | None = None,
    max_files: int = 250,
) -> list[tuple[str, str]]:
    """Fetch every ``docs/md/**/*.md`` file from the repo's default branch.

    The markdown counterpart to :func:`fetch_html_docs`: a project opts a
    markdown page into its portfolio docs by committing it under ``docs/md/``.
    Returns ``(path, raw_markdown)`` tuples (e.g. ``docs/md/roadmap.md``).
    """
    return _fetch_docs_under(
        owner, repo, DOCS_MD_PREFIX, ".md",
        default_branch=default_branch, max_files=max_files,
    )


def fetch_commits(
    owner: str,
    repo: str,
    *,
    since: str | None = None,
    until: str | None = None,
    max_pages: int = 10,
) -> list[dict[str, str]]:
    """List commits for *owner/repo*, newest first, across pages.

    Returns ``[{"sha", "message", "date"}]`` where *message* is the commit's
    first line and *date* is the author date (ISO-8601 Z). *since*/*until* are
    forwarded to the API to bound the window. Returns an empty list for a missing
    (404) or empty (409) repo. Caps at *max_pages* to bound cost.
    """
    session = _session()
    out: list[dict[str, str]] = []
    page = 1
    while page <= max_pages:
        params: dict[str, object] = {"per_page": PER_PAGE, "page": page}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        resp = session.get(f"{API_BASE}/repos/{owner}/{repo}/commits", params=params)
        if resp.status_code in (404, 409):  # missing repo / empty repo (no commits)
            return out
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        for c in data:
            commit = c.get("commit") or {}
            msg = (commit.get("message") or "").splitlines()
            first_line = msg[0].strip() if msg else ""
            date = (commit.get("author") or {}).get("date") or (
                commit.get("committer") or {}
            ).get("date") or ""
            out.append({"sha": c.get("sha", ""), "message": first_line, "date": date})
        if len(data) < PER_PAGE:
            break
        page += 1
    return out


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


def fetch_merged_prs(owner: str, repo: str, since: str | None = None) -> list[dict[str, Any]]:
    """Merged PRs for owner/repo, ascending by merged_at; only newer than `since`."""
    session = _session()
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/pulls",
            params={"state": "closed", "sort": "updated", "direction": "desc",
                    "per_page": 100, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for pr in batch:
            if not pr.get("merged_at"):
                continue
            if since and pr["merged_at"] <= since:
                continue
            out.append({
                "number": pr["number"],
                "title": pr.get("title", ""),
                "body": pr.get("body") or "",
                "merged_at": pr["merged_at"],
                "merge_commit_sha": pr.get("merge_commit_sha"),
                "labels": [l["name"] for l in pr.get("labels", [])],
            })
        if len(batch) < 100:
            break
        page += 1
    out.sort(key=lambda p: p["merged_at"])
    return out


def fetch_pr_files(owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Changed files for a PR: [{path, status, adds, dels, patch}]."""
    session = _session()
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/files",
            params={"per_page": 100, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for f in batch:
            out.append({
                "path": f.get("filename", ""),
                "status": f.get("status", ""),
                "adds": f.get("additions", 0),
                "dels": f.get("deletions", 0),
                "patch": f.get("patch", ""),
            })
        if len(batch) < 100:
            break
        page += 1
    return out
