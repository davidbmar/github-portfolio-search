import pytest
from ghps.narrate.reduce import build_pr_record
from ghps.narrate.schema import NarrateValidationError

class _FakeClient:
    def __init__(self, payload): self.payload = payload
    def complete_json(self, system, user): return dict(self.payload)

_GOOD = {"problem": "p", "approach": "a", "components": ["c"], "apis_changed": ["x"],
         "tests_changed": ["t"], "reusable_pattern": True, "risks": ["r"]}

def test_build_pr_record_assembles_and_validates():
    pr = {"number": 5, "repo": "riff", "title": "t", "body": "b",
          "merged_at": "2026-06-21T00:00:00Z", "merge_commit_sha": "sha", "labels": ["feat"]}
    files = [{"path": "src/a.py", "status": "modified", "adds": 3, "dels": 0, "patch": "diff"}]
    rec = build_pr_record(pr, files, _FakeClient(_GOOD), model="qwen3.7-plus")
    assert rec["pr_number"] == 5 and rec["repo"] == "riff"
    assert rec["files_hash"] and rec["merge_commit_sha"] == "sha"
    assert rec["reusable_pattern"] is True

def test_build_pr_record_raises_on_bad_llm():
    pr = {"number": 5, "repo": "riff", "title": "t", "body": "",
          "merged_at": "2026-06-21T00:00:00Z", "merge_commit_sha": "sha", "labels": []}
    files = [{"path": "a.py", "status": "modified", "adds": 1, "dels": 0, "patch": ""}]
    with pytest.raises(NarrateValidationError):
        build_pr_record(pr, files, _FakeClient({"problem": "only"}), model="m")
