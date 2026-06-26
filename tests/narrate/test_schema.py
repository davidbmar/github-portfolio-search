import pytest
from ghps.narrate.schema import (
    files_hash, make_slug, validate_pr_record, validate_theme_record,
    NarrateValidationError, THEME_STATES,
)

def test_files_hash_is_order_independent():
    a = [{"path": "a.py", "status": "modified", "adds": 1, "dels": 0},
         {"path": "b.py", "status": "added", "adds": 5, "dels": 0}]
    assert files_hash(a) == files_hash(list(reversed(a)))

def test_files_hash_changes_on_content():
    a = [{"path": "a.py", "status": "modified", "adds": 1, "dels": 0}]
    b = [{"path": "a.py", "status": "modified", "adds": 2, "dels": 0}]
    assert files_hash(a) != files_hash(b)

def test_make_slug_kebab():
    assert make_slug("LLM-judge Routing (wins)!") == "llm-judge-routing-wins"

def test_validate_pr_record_rejects_missing_keys():
    with pytest.raises(NarrateValidationError):
        validate_pr_record({"pr_number": 1})

def test_validate_theme_record_rejects_bad_status():
    rec = {k: "x" for k in ("theme_id", "slug", "title")}
    rec.update({"status": "bogus", "repos": ["r"], "pr_numbers": [1],
                "summary": "s", "narrative": "n"})
    with pytest.raises(NarrateValidationError):
        validate_theme_record(rec)

def test_theme_states_constant():
    assert THEME_STATES == ("candidate", "mature", "published", "archived")

def test_validate_pr_record_allows_empty_arrays():
    # a pure-refactor PR: no apis/tests/components/risks changed -> still valid
    rec = {"pr_number": 6, "repo": "riff", "merged_at": "2026-06-10T00:00:00Z",
           "title": "refactor internals", "problem": "p", "approach": "a",
           "components": [], "apis_changed": [], "tests_changed": [],
           "reusable_pattern": False, "risks": [], "files": [{"path": "a.py"}]}
    validate_pr_record(rec)  # must NOT raise

def test_validate_pr_record_rejects_empty_scalar():
    rec = {"pr_number": 6, "repo": "riff", "merged_at": "2026-06-10T00:00:00Z",
           "title": "", "problem": "p", "approach": "a",
           "components": [], "apis_changed": [], "tests_changed": [],
           "reusable_pattern": False, "risks": [], "files": [{"path": "a.py"}]}
    with pytest.raises(NarrateValidationError):
        validate_pr_record(rec)

def test_validate_pr_record_rejects_missing_array_key():
    rec = {"pr_number": 6, "repo": "riff", "merged_at": "2026-06-10T00:00:00Z",
           "title": "t", "problem": "p", "approach": "a",
           "components": [], "tests_changed": [], "reusable_pattern": False,
           "risks": [], "files": [{"path": "a.py"}]}  # apis_changed KEY missing
    with pytest.raises(NarrateValidationError):
        validate_pr_record(rec)
