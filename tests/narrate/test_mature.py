from ghps.narrate.store import Store
from ghps.narrate.mature import score_theme, apply_lifecycle

def _pr(n, **kw):
    base = {"repo": "riff", "pr_number": n, "tests_changed": [], "apis_changed": [],
            "reusable_pattern": False, "files": [], "labels": []}
    base.update(kw); return base

def test_score_counts_prs_and_signals():
    prs = [_pr(1, tests_changed=["t"], reusable_pattern=True, apis_changed=["a"])]
    score, reason = score_theme({"pr_numbers": [1]}, prs)
    assert score == 2 + 2 + 2 + 2          # pr + tests + apis + reusable
    assert "reusable" in reason.lower()

def test_apply_lifecycle_promotes_at_threshold(tmp_path):
    store = Store(tmp_path)
    store.put_theme({"theme_id": "t1", "slug": "s", "title": "T", "status": "candidate",
                     "pr_numbers": [1, 2, 3], "repos": ["riff"]})
    for n in (1, 2, 3):
        store.put_pr(_pr(n, tests_changed=["t"]))
    matured = apply_lifecycle(store, mature_at=7)
    assert store.get_theme("t1")["status"] == "mature"
    assert [t["theme_id"] for t in matured] == ["t1"]
