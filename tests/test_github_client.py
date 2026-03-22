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
