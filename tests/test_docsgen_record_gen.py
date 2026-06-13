"""Unit tests for record generation (LLM client is a fake)."""

from __future__ import annotations

import pytest

from ghps.docsgen import record_gen
from ghps.docsgen.context import RepoContext


def _ctx(**overrides) -> RepoContext:
    base = dict(
        slug="demo",
        owner="davidbmar",
        repo_url="https://github.com/davidbmar/demo",
        visibility="public",
        default_branch="main",
        head_sha="abc1234",
        description="A demo",
        language="Python",
        topics=["demo"],
        readme="# Demo\n\nDoes a thing.",
        source_files=[("main.py", "print('hi')")],
        branch_status=[{"name": "feat/x", "ahead_by": 2}],
        open_prs=[],
        thin=False,
    )
    base.update(overrides)
    return RepoContext(**base)


# A complete LLM-authored half of the record (the fields the model owns).
_LLM_FIELDS = {
    "title": "Demo Project",
    "one_liner": "Does a thing.",
    "what_it_is": "A demonstration.",
    "how_its_built": "Built with Python.",
    "how_to_apply": "Copy it.",
    "quickstart": "pip install demo && demo run",
    "features": ["does the thing"],
    "diagram_architecture": "flowchart LR; A-->B",
    "diagram_sequence": "sequenceDiagram; A->>B: hi",
    "capabilities": ["demoing"],
    "components": ["main"],
    "tech": ["python"],
    "depends_on": [],
    "integrates_with": [],
    "patterns": ["adapter"],
    "reuse_tags": ["demo"],
}


class _FakeClient:
    model = "fake-model"

    def __init__(self, *returns):
        self._returns = list(returns)
        self.calls = 0

    def complete_json(self, system, user):
        self.calls += 1
        # Repeat the last supplied return if called more often than seeded, so
        # the test fails on the assertion under test rather than an IndexError.
        return self._returns.pop(0) if len(self._returns) > 1 else self._returns[0]


def test_generates_valid_record_and_fills_deterministic_fields():
    client = _FakeClient(dict(_LLM_FIELDS))
    rec = record_gen.generate_record(_ctx(), client)
    assert rec["slug"] == "demo"
    assert rec["repo_url"] == "https://github.com/davidbmar/demo"
    assert rec["visibility"] == "public"
    assert rec["thin"] is False
    assert rec["source_commit"] == "abc1234"
    assert rec["model"] == "fake-model"
    # hygiene derived, not from LLM
    assert rec["todos"][0]["kind"] == "unmerged_branch"
    # provenance timestamp present
    assert rec["generated_at"].endswith("Z")
    assert record_gen.schema.validate_record(rec) == []


def test_llm_supplied_deterministic_fields_are_overridden():
    """Untrusted LLM output can never populate generator-owned fields."""
    poisoned = dict(_LLM_FIELDS)
    poisoned["slug"] = "INJECTED"
    poisoned["repo_url"] = "https://evil.example.com"
    poisoned["visibility"] = "private"
    poisoned["thin"] = True
    poisoned["status"] = "idea"
    poisoned["source_commit"] = "deadbee"
    poisoned["model"] = "evil-model"
    poisoned["todos"] = [{"kind": "injected", "detail": "bad"}]
    client = _FakeClient(poisoned)
    rec = record_gen.generate_record(_ctx(), client)
    assert rec["slug"] == "demo"
    assert rec["repo_url"] == "https://github.com/davidbmar/demo"
    assert rec["visibility"] == "public"
    assert rec["thin"] is False
    assert rec["status"] == "shipped"
    assert rec["source_commit"] == "abc1234"
    assert rec["model"] == "fake-model"
    # todos derived from hygiene (branch_status), not taken from LLM
    assert all(t["kind"] != "injected" for t in rec["todos"])
    assert rec["todos"][0]["kind"] == "unmerged_branch"


def test_retries_once_on_invalid_then_succeeds():
    bad = dict(_LLM_FIELDS)
    del bad["what_it_is"]  # invalid → triggers retry
    client = _FakeClient(bad, dict(_LLM_FIELDS))
    rec = record_gen.generate_record(_ctx(), client)
    assert client.calls == 2
    assert record_gen.schema.validate_record(rec) == []


def test_raises_after_retry_exhausted():
    bad = dict(_LLM_FIELDS)
    del bad["how_its_built"]
    client = _FakeClient(bad, bad)
    with pytest.raises(record_gen.RecordGenerationError):
        record_gen.generate_record(_ctx(), client)


def test_non_dict_llm_response_raises_record_error_not_attributeerror():
    """Valid-but-non-dict JSON (e.g. a list) must not crash — it retries then raises."""
    client = _FakeClient([1, 2, 3], [1, 2, 3])
    with pytest.raises(record_gen.RecordGenerationError):
        record_gen.generate_record(_ctx(), client)


def test_thin_repo_still_produces_valid_record():
    client = _FakeClient(dict(_LLM_FIELDS))
    rec = record_gen.generate_record(_ctx(thin=True, readme="", source_files=[]), client)
    assert rec["thin"] is True
    assert record_gen.schema.validate_record(rec) == []
