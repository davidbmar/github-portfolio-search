from ghps.narrate.store import Store
from ghps.narrate.cluster import classify_pr

class _Client:
    def __init__(self, payload): self.payload = payload
    def complete_json(self, system, user): return dict(self.payload)

def _pr(n=1):
    return {"repo": "riff", "pr_number": n, "title": "LLM judge routing",
            "problem": "p", "approach": "a", "components": ["router"], "apis_changed": []}

def test_high_cosine_attaches_without_llm(tmp_path):
    store = Store(tmp_path)
    store.put_theme({"theme_id": "t1", "slug": "llm-judge-routing", "title": "x",
                     "embedding": [1.0, 0.0], "pr_numbers": [], "repos": []})
    d = classify_pr(_pr(), [1.0, 0.0], store, _Client({}), model="m")
    assert d["action"] == "attach" and d["theme_id"] == "t1"
    assert "riff#1" in store.get_theme("t1")["pr_numbers"]

def test_no_themes_creates_with_immutable_slug(tmp_path):
    store = Store(tmp_path)
    d = classify_pr(_pr(), [0.1, 0.9], store,
                    _Client({"action": "create", "title": "LLM Judge Routing"}), model="m")
    assert d["action"] == "create"
    assert store.get_theme(d["theme_id"])["slug"] == "llm-judge-routing"

def test_ledger_idempotent(tmp_path):
    store = Store(tmp_path)
    c = _Client({"action": "create", "title": "T"})
    d1 = classify_pr(_pr(7), [0.1, 0.9], store, c, model="m")
    d2 = classify_pr(_pr(7), [0.1, 0.9], store, c, model="m")
    assert d1["theme_id"] == d2["theme_id"]
    assert len([t for t in store.all_themes()]) == 1   # not duplicated

def test_unknown_llm_action_falls_back_to_ignore(tmp_path):
    store = Store(tmp_path)
    # low cosine path with no themes -> goes to LLM; LLM returns a bogus action
    d = classify_pr(_pr(9), [0.1, 0.9], store, _Client({"action": "defer"}), model="m")
    assert d["action"] == "ignore"
    assert d["theme_id"] is None
    assert store.all_themes() == []                 # nothing created
    assert store.ledger_decision("riff", 9) is not None  # ledger entry written

def test_attach_with_bogus_theme_id_falls_back_to_candidate(tmp_path):
    store = Store(tmp_path)
    store.put_theme({"theme_id": "t1", "slug": "s", "title": "x",
                     "embedding": [1.0, 0.0], "pr_numbers": [], "repos": []})
    # pr vec at cosine ~0.70 to [1,0] -> mid-confidence band, LLM consulted
    d = classify_pr(_pr(), [0.70, 0.714], store,
                    _Client({"action": "attach", "theme_id": "does-not-exist"}), model="m")
    assert d["action"] == "attach" and d["theme_id"] == "t1"   # fell back to the real candidate, no crash
