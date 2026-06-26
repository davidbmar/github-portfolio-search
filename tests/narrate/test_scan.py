from ghps.narrate.store import Store
from ghps.narrate.scan import scan_repo


def _fake_fetch(prs):
    def _f(owner, repo, since=None):
        return [p for p in prs if since is None or p["merged_at"] > since]
    return _f


def test_scan_returns_new_and_advances_cursor(tmp_path):
    store = Store(tmp_path)
    prs = [{"number": 1, "merged_at": "2026-06-19T00:00:00Z", "title": "a"},
           {"number": 2, "merged_at": "2026-06-21T00:00:00Z", "title": "b"}]
    new = scan_repo("o", "riff", store, fetch=_fake_fetch(prs))
    assert [p["number"] for p in new] == [1, 2]
    assert store.read_cursor("riff") == "2026-06-21T00:00:00Z"


def test_scan_skips_already_stored(tmp_path):
    store = Store(tmp_path)
    store.put_pr({"repo": "riff", "pr_number": 1, "merged_at": "2026-06-19T00:00:00Z"})
    prs = [{"number": 1, "merged_at": "2026-06-19T00:00:00Z", "title": "a"},
           {"number": 2, "merged_at": "2026-06-21T00:00:00Z", "title": "b"}]
    new = scan_repo("o", "riff", store, fetch=_fake_fetch(prs))
    assert [p["number"] for p in new] == [2]
