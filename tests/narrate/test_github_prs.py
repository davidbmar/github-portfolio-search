"""Tests for GitHub PR fetchers (merged PRs and PR files)."""

from ghps import github_client as gc


class _Resp:
    def __init__(self, data):
        self._data = data
        self.status_code = 200
        self.headers = {}

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


class _FakeSession:
    def __init__(self, routes):
        self.routes = routes

    def get(self, url, params=None, **kw):
        for frag, data in self.routes.items():
            if frag in url:
                return _Resp(data)
        return _Resp([])


def test_fetch_merged_prs_filters_and_sorts(monkeypatch):
    prs = [
        {
            "number": 2,
            "merged_at": "2026-06-21T00:00:00Z",
            "title": "b",
            "body": "",
            "merge_commit_sha": "s2",
            "labels": [{"name": "feat"}],
        },
        {
            "number": 1,
            "merged_at": "2026-06-19T00:00:00Z",
            "title": "a",
            "body": "",
            "merge_commit_sha": "s1",
            "labels": [],
        },
        {
            "number": 3,
            "merged_at": None,
            "title": "open",
            "body": "",
            "merge_commit_sha": None,
            "labels": [],
        },
    ]
    monkeypatch.setattr(gc, "_session", lambda: _FakeSession({"/pulls": prs}))
    out = gc.fetch_merged_prs("o", "r", since="2026-06-20T00:00:00Z")
    assert [p["number"] for p in out] == [2]  # #1 too old, #3 not merged
    assert out[0]["labels"] == ["feat"]


def test_fetch_pr_files_shape(monkeypatch):
    files = [
        {
            "filename": "a.py",
            "status": "modified",
            "additions": 3,
            "deletions": 1,
            "patch": "@@ -1 +1 @@",
        }
    ]
    monkeypatch.setattr(gc, "_session", lambda: _FakeSession({"/files": files}))
    out = gc.fetch_pr_files("o", "r", 7)
    assert out[0] == {
        "path": "a.py",
        "status": "modified",
        "adds": 3,
        "dels": 1,
        "patch": "@@ -1 +1 @@",
    }
