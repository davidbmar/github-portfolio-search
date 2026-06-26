from ghps.narrate.store import Store
from ghps.narrate.mature import score_theme, apply_lifecycle

def _pr(n, **kw):
    base = {"repo": "riff", "pr_number": n, "tests_changed": [], "apis_changed": [],
            "reusable_pattern": False, "files": [], "labels": []}
    base.update(kw); return base

def test_score_counts_prs_and_signals():
    prs = [_pr(1, tests_changed=["t"], reusable_pattern=True, apis_changed=["a"])]
    score, reason = score_theme({"pr_numbers": ["riff#1"]}, prs)
    assert score == 2 + 2 + 2 + 2          # pr + tests + apis + reusable
    assert "reusable" in reason.lower()

def test_apply_lifecycle_promotes_at_threshold(tmp_path):
    store = Store(tmp_path)
    store.put_theme({"theme_id": "t1", "slug": "s", "title": "T", "status": "candidate",
                     "pr_numbers": ["riff#1", "riff#2", "riff#3"], "repos": ["riff"]})
    for n in (1, 2, 3):
        store.put_pr(_pr(n, tests_changed=["t"]))
    matured = apply_lifecycle(store, mature_at=7)
    assert store.get_theme("t1")["status"] == "mature"
    assert [t["theme_id"] for t in matured] == ["t1"]


def test_score_theme_ignores_other_repo_same_pr_number():
    prs = [_pr(5, repo="riff", tests_changed=["t"]),
           _pr(5, repo="other", reusable_pattern=True, apis_changed=["x"])]
    score, _ = score_theme({"pr_numbers": ["riff#5"]}, prs)
    assert score == 4   # only riff#5: 1 PR (+2) + tests (+2); other#5 excluded
