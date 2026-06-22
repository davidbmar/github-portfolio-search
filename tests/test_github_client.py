"""Unit tests for ghps.github_client — all HTTP calls are mocked."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from ghps import github_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data, status_code=200):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _repo_payload(name: str, **overrides):
    """Build a single GitHub repo JSON object."""
    base = {
        "name": name,
        "description": f"Description for {name}",
        "language": "Python",
        "topics": ["topic-a"],
        "stargazers_count": 5,
        "updated_at": "2025-01-01T00:00:00Z",
        "html_url": f"https://github.com/user/{name}",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# fetch_repos
# ---------------------------------------------------------------------------

class TestFetchRepos:
    @patch.object(github_client, "_session")
    def test_single_page(self, mock_session_fn):
        """Repos fitting in one page are returned correctly."""
        session = MagicMock()
        mock_session_fn.return_value = session

        repos = [_repo_payload(f"repo-{i}") for i in range(3)]
        session.get.return_value = _mock_response(repos)

        result = github_client.fetch_repos("user")

        assert len(result) == 3
        assert result[0]["name"] == "repo-0"
        assert result[0]["description"] == "Description for repo-0"
        assert result[0]["language"] == "Python"
        assert result[0]["topics"] == ["topic-a"]
        assert result[0]["stars"] == 5
        assert result[0]["html_url"] == "https://github.com/user/repo-0"

    @patch.object(github_client, "_session")
    def test_captures_pushed_at(self, mock_session_fn):
        """pushed_at (last push time) is captured for staleness checks."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response(
            [_repo_payload("r", pushed_at="2026-06-01T00:00:00Z")]
        )
        result = github_client.fetch_repos("user")
        assert result[0]["pushed_at"] == "2026-06-01T00:00:00Z"

    @patch.object(github_client, "_session")
    def test_pagination(self, mock_session_fn):
        """Users with >100 repos trigger multiple pages."""
        session = MagicMock()
        mock_session_fn.return_value = session

        page1 = [_repo_payload(f"repo-{i}") for i in range(100)]
        page2 = [_repo_payload(f"repo-{i}") for i in range(100, 130)]

        session.get.side_effect = [
            _mock_response(page1),
            _mock_response(page2),
        ]

        result = github_client.fetch_repos("user")
        assert len(result) == 130
        assert session.get.call_count == 2

    @patch.object(github_client, "_session")
    def test_missing_optional_fields(self, mock_session_fn):
        """Repos with null description/language get empty strings."""
        session = MagicMock()
        mock_session_fn.return_value = session

        repos = [_repo_payload("bare", description=None, language=None, topics=[])]
        session.get.return_value = _mock_response(repos)

        result = github_client.fetch_repos("user")
        assert result[0]["description"] == ""
        assert result[0]["language"] == ""
        assert result[0]["topics"] == []


# ---------------------------------------------------------------------------
# fetch_readme
# ---------------------------------------------------------------------------

class TestFetchReadme:
    @patch.object(github_client, "_session")
    def test_returns_decoded_content(self, mock_session_fn):
        """README content is base64-decoded."""
        session = MagicMock()
        mock_session_fn.return_value = session

        raw = "# Hello World"
        encoded = base64.b64encode(raw.encode()).decode()
        session.get.return_value = _mock_response({
            "content": encoded,
            "encoding": "base64",
        })

        result = github_client.fetch_readme("owner", "repo")
        assert result == "# Hello World"

    @patch.object(github_client, "_session")
    def test_missing_readme_returns_empty(self, mock_session_fn):
        """Repos without a README return an empty string."""
        session = MagicMock()
        mock_session_fn.return_value = session

        resp = MagicMock()
        resp.status_code = 404
        session.get.return_value = resp

        result = github_client.fetch_readme("owner", "repo")
        assert result == ""


# ---------------------------------------------------------------------------
# fetch_top_files
# ---------------------------------------------------------------------------

class TestFetchTopFiles:
    @patch.object(github_client, "_session")
    def test_fetches_matching_files(self, mock_session_fn):
        """Only files with matching extensions are fetched."""
        session = MagicMock()
        mock_session_fn.return_value = session

        repo_resp = _mock_response({"default_branch": "main"})
        tree_resp = _mock_response({
            "tree": [
                {"path": "src/main.py", "type": "blob", "sha": "abc123"},
                {"path": "README.md", "type": "blob", "sha": "def456"},
                {"path": "lib", "type": "tree", "sha": "ghi789"},
            ]
        })

        file_content = "print('hello')"
        encoded = base64.b64encode(file_content.encode()).decode()
        blob_resp = _mock_response({"content": encoded, "encoding": "base64"})

        session.get.side_effect = [repo_resp, tree_resp, blob_resp]

        result = github_client.fetch_top_files("owner", "repo")

        assert len(result) == 1
        assert result[0] == ("src/main.py", "print('hello')")

    @patch.object(github_client, "_session")
    def test_repo_not_found(self, mock_session_fn):
        """Returns empty list if repo doesn't exist."""
        session = MagicMock()
        mock_session_fn.return_value = session

        resp = MagicMock()
        resp.status_code = 404
        session.get.return_value = resp

        result = github_client.fetch_top_files("owner", "nonexistent")
        assert result == []

    @patch.object(github_client, "_session")
    def test_empty_repo_409_returns_empty(self, mock_session_fn):
        """An empty repo returns 409 on the trees endpoint — skip, don't crash."""
        session = MagicMock()
        mock_session_fn.return_value = session
        repo_resp = _mock_response({"default_branch": "main"})
        tree_resp = MagicMock()
        tree_resp.status_code = 409  # GitHub: "Git Repository is empty"
        session.get.side_effect = [repo_resp, tree_resp]
        assert github_client.fetch_top_files("owner", "empty-repo") == []

    @patch.object(github_client, "_session")
    def test_custom_extensions(self, mock_session_fn):
        """Custom extensions filter correctly."""
        session = MagicMock()
        mock_session_fn.return_value = session

        repo_resp = _mock_response({"default_branch": "main"})
        tree_resp = _mock_response({
            "tree": [
                {"path": "index.html", "type": "blob", "sha": "a1"},
                {"path": "style.css", "type": "blob", "sha": "b2"},
                {"path": "app.js", "type": "blob", "sha": "c3"},
            ]
        })

        content = base64.b64encode(b"<html></html>").decode()
        blob_resp = _mock_response({"content": content, "encoding": "base64"})

        session.get.side_effect = [repo_resp, tree_resp, blob_resp]

        result = github_client.fetch_top_files(
            "owner", "repo", extensions=[".html"]
        )

        assert len(result) == 1
        assert result[0][0] == "index.html"

    @patch.object(github_client, "_session")
    def test_default_branch_skips_repo_lookup(self, mock_session_fn):
        """Passing default_branch avoids the extra GET /repos call."""
        session = MagicMock()
        mock_session_fn.return_value = session

        tree_resp = _mock_response({
            "tree": [{"path": "a.py", "type": "blob", "sha": "s1"}]
        })
        blob_resp = _mock_response(
            {"content": base64.b64encode(b"x").decode(), "encoding": "base64"}
        )
        # Only tree + blob calls — NO repo lookup first.
        session.get.side_effect = [tree_resp, blob_resp]

        result = github_client.fetch_top_files("owner", "repo", default_branch="main")
        assert result == [("a.py", "x")]
        # first call is the tree endpoint, not /repos/owner/repo
        assert "git/trees/main" in session.get.call_args_list[0].args[0]

    @patch.object(github_client, "_session")
    def test_max_files_caps_blob_downloads(self, mock_session_fn):
        """max_files limits how many blobs are fetched (not all matching files)."""
        session = MagicMock()
        mock_session_fn.return_value = session

        tree_resp = _mock_response({
            "tree": [
                {"path": f"f{i}.py", "type": "blob", "sha": f"s{i}"} for i in range(10)
            ]
        })
        blob_resp = _mock_response(
            {"content": base64.b64encode(b"x").decode(), "encoding": "base64"}
        )
        # tree + exactly 2 blob fetches (capped), nothing more.
        session.get.side_effect = [tree_resp, blob_resp, blob_resp]

        result = github_client.fetch_top_files(
            "owner", "repo", default_branch="main", max_files=2
        )
        assert len(result) == 2
        # 1 tree call + 2 blob calls = 3 total (no repo lookup, no 10 blobs)
        assert session.get.call_count == 3


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuth:
    @patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test123"})
    def test_token_sets_auth_header(self):
        """GITHUB_TOKEN env var is used in Authorization header."""
        session = github_client._session()
        assert session.headers["Authorization"] == "Bearer ghp_test123"

    @patch.dict("os.environ", {}, clear=True)
    def test_no_token_no_header(self):
        """Without GITHUB_TOKEN, no Authorization header is set."""
        session = github_client._session()
        assert "Authorization" not in session.headers


# ---------------------------------------------------------------------------
# fetch_branches / compare_commits / fetch_open_prs  (L0 hygiene)
# ---------------------------------------------------------------------------

class TestFetchBranches:
    @patch.object(github_client, "_session")
    def test_lists_branches_with_sha(self, mock_session_fn):
        """Branches are returned as name + commit_sha pairs."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([
            {"name": "main", "commit": {"sha": "aaa111"}},
            {"name": "feat/x", "commit": {"sha": "bbb222"}},
        ])

        result = github_client.fetch_branches("owner", "repo")
        assert result == [
            {"name": "main", "commit_sha": "aaa111"},
            {"name": "feat/x", "commit_sha": "bbb222"},
        ]

    @patch.object(github_client, "_session")
    def test_repo_not_found_returns_empty(self, mock_session_fn):
        """A 404 (missing repo) yields an empty branch list."""
        session = MagicMock()
        mock_session_fn.return_value = session
        resp = MagicMock()
        resp.status_code = 404
        session.get.return_value = resp

        assert github_client.fetch_branches("owner", "missing") == []


class TestCompareCommits:
    @patch.object(github_client, "_session")
    def test_returns_ahead_by(self, mock_session_fn):
        """ahead_by from the compare API is returned as an int."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response({"ahead_by": 4})

        assert github_client.compare_commits("owner", "repo", "main", "feat/x") == 4

    @patch.object(github_client, "_session")
    def test_missing_comparison_returns_zero(self, mock_session_fn):
        """A non-200 comparison (e.g. 404) is treated as 0 ahead."""
        session = MagicMock()
        mock_session_fn.return_value = session
        resp = MagicMock()
        resp.status_code = 404
        session.get.return_value = resp

        assert github_client.compare_commits("owner", "repo", "main", "x") == 0


class TestFetchOpenPRs:
    @patch.object(github_client, "_session")
    def test_returns_number_and_title(self, mock_session_fn):
        """Open PRs are projected to number + title."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([
            {"number": 7, "title": "Add feature", "draft": False},
            {"number": 9, "title": "Fix bug", "draft": False},
        ])

        result = github_client.fetch_open_prs("owner", "repo")
        assert result == [
            {"number": 7, "title": "Add feature"},
            {"number": 9, "title": "Fix bug"},
        ]

    @patch.object(github_client, "_session")
    def test_no_prs_returns_empty(self, mock_session_fn):
        """No open PRs yields an empty list."""
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([])

        assert github_client.fetch_open_prs("owner", "repo") == []

    @patch.object(github_client, "_session")
    def test_pagination(self, mock_session_fn):
        """Repos with >100 open PRs trigger multiple pages."""
        session = MagicMock()
        mock_session_fn.return_value = session
        page1 = [{"number": i, "title": f"PR {i}"} for i in range(100)]
        page2 = [{"number": i, "title": f"PR {i}"} for i in range(100, 130)]
        session.get.side_effect = [_mock_response(page1), _mock_response(page2)]

        result = github_client.fetch_open_prs("owner", "repo")
        assert len(result) == 130
        assert session.get.call_count == 2


# ---------------------------------------------------------------------------
# fetch_commits
# ---------------------------------------------------------------------------

class TestFetchCommits:
    @patch.object(github_client, "_session")
    def test_returns_sha_message_firstline_date(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        commits = [
            {"sha": "abc123", "commit": {"message": "feat: x\n\nlong body",
                                         "author": {"date": "2026-06-20T04:00:00Z"}}},
            {"sha": "def456", "commit": {"message": "fix: y",
                                         "author": {"date": "2026-06-19T10:00:00Z"}}},
        ]
        session.get.return_value = _mock_response(commits)  # 2 < PER_PAGE -> one page
        out = github_client.fetch_commits("o", "r")
        assert out == [
            {"sha": "abc123", "message": "feat: x", "date": "2026-06-20T04:00:00Z"},
            {"sha": "def456", "message": "fix: y", "date": "2026-06-19T10:00:00Z"},
        ]

    @patch.object(github_client, "_session")
    def test_empty_repo_409_returns_empty(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([], status_code=409)
        assert github_client.fetch_commits("o", "r") == []

    @patch.object(github_client, "_session")
    def test_missing_repo_404_returns_empty(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([], status_code=404)
        assert github_client.fetch_commits("o", "r") == []

    @patch.object(github_client, "_session")
    def test_since_is_forwarded_as_param(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([])
        github_client.fetch_commits("o", "r", since="2026-06-01T00:00:00Z")
        _, kwargs = session.get.call_args
        assert kwargs["params"].get("since") == "2026-06-01T00:00:00Z"
