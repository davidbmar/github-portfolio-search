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
