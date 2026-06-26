from ghps.narrate.store import Store
from ghps.narrate.pipeline import run


class _Embedder:
    def embed_text(self, text): return [1.0, 0.0]


class _Client:
    def complete_json(self, system, user):
        if "APPLIED TUTORIAL" in system:
            return {"summary": "S", "narrative": "N", "principles": ["p"],
                    "patterns": ["pat"], "applied_examples": ["ex"], "pitfalls": ["pit"]}
        if "REUSABLE facts" in system:
            return {"problem": "p", "approach": "a", "components": ["c"], "apis_changed": ["x"],
                    "tests_changed": ["t"], "reusable_pattern": True, "risks": ["r"]}
        return {"action": "create", "title": "LLM Judge Routing"}


def test_run_end_to_end(tmp_path, monkeypatch):
    store = Store(tmp_path / "state")
    prs = [{"number": n, "merged_at": f"2026-06-2{n}T00:00:00Z", "title": "t",
            "body": "", "merge_commit_sha": f"s{n}", "labels": ["feat"]} for n in (1, 2, 3)]
    def fake_scan(owner, repo, st, **kw):
        for p in prs: p["repo"] = repo
        return prs
    def fake_files(owner, repo, n):
        return [{"path": "src/a.py", "status": "modified", "adds": 5, "dels": 0, "patch": "diff"},
                {"path": "tests/test_a.py", "status": "added", "adds": 9, "dels": 0, "patch": "assert"}]
    out = run("o", ["riff"], store, _Client(), _Embedder(), tmp_path / "learn",
              model="qwen3.7-plus", fetch_files=fake_files, scan_fn=fake_scan)
    assert out["prs"] == 3
    assert out["themes_matured"] >= 1
    assert any("index.html" in p for p in out["pages"])


def test_published_theme_not_rerendered_on_second_run(tmp_path):
    store = Store(tmp_path / "state")
    prs = [{"number": n, "merged_at": f"2026-06-2{n}T00:00:00Z", "title": "t",
            "body": "", "merge_commit_sha": f"s{n}", "labels": ["feat"]} for n in (1, 2, 3)]
    calls = {"tutorial": 0}

    class _CountingClient(_Client):
        def complete_json(self, system, user):
            if "APPLIED TUTORIAL" in system:
                calls["tutorial"] += 1
            return super().complete_json(system, user)

    def fake_files(owner, repo, n):
        return [{"path": "src/a.py", "status": "modified", "adds": 5, "dels": 0, "patch": "diff"},
                {"path": "tests/test_a.py", "status": "added", "adds": 9, "dels": 0, "patch": "assert"}]

    seen = {"done": False}

    def scan_once(owner, repo, st, **kw):
        if seen["done"]:
            return []
        seen["done"] = True
        for p in prs:
            p["repo"] = repo
        return prs

    client = _CountingClient()
    out1 = run("o", ["riff"], store, client, _Embedder(), tmp_path / "learn",
               model="m", fetch_files=fake_files, scan_fn=scan_once)
    out2 = run("o", ["riff"], store, client, _Embedder(), tmp_path / "learn",
               model="m", fetch_files=fake_files, scan_fn=scan_once)
    assert out1["themes_matured"] >= 1
    assert out2["themes_matured"] == 0          # nothing new matured
    assert calls["tutorial"] == out1["themes_matured"]   # LLM prose billed once, not twice
