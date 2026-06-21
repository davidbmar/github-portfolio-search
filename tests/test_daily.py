"""Unit tests for the daily-headline-digest data layer.

Pure logic (aggregation, digest assembly, deterministic engine, JSON write) is
tested directly; the LLM engine is injected, so the suite never calls codex/MLX.
"""

from __future__ import annotations

import json

from ghps import daily


# ---------------------------------------------------------------------------
# aggregate_by_day
# ---------------------------------------------------------------------------

def test_aggregate_buckets_commits_by_utc_day():
    repo_commits = {
        "alpha": [
            {"sha": "a1", "message": "fix one", "date": "2026-06-20T04:03:27Z"},
            {"sha": "a2", "message": "fix two", "date": "2026-06-19T23:10:00Z"},
        ],
        "beta": [
            {"sha": "b1", "message": "feat x", "date": "2026-06-20T11:00:00Z"},
        ],
    }
    days = daily.aggregate_by_day(repo_commits)
    assert set(days) == {"2026-06-20", "2026-06-19"}
    # day 06-20 has alpha/a1 and beta/b1
    repos_2020 = {c["repo"] for c in days["2026-06-20"]}
    assert repos_2020 == {"alpha", "beta"}
    assert days["2026-06-19"][0]["repo"] == "alpha"


def test_aggregate_ignores_commits_without_a_date():
    days = daily.aggregate_by_day({"alpha": [{"sha": "x", "message": "m", "date": ""}]})
    assert days == {}


# ---------------------------------------------------------------------------
# DeterministicEngine (no LLM)
# ---------------------------------------------------------------------------

def test_deterministic_engine_summarizes_without_an_llm():
    eng = daily.DeterministicEngine()
    out = eng.generate("2026-06-20", ["alpha: fix one", "beta: feat x", "alpha: fix two"])
    assert "3" in out["headline"]          # 3 commits
    assert "2" in out["headline"]          # 2 repos
    assert out["summary"]                  # non-empty


# ---------------------------------------------------------------------------
# build_digests
# ---------------------------------------------------------------------------

class _FakeEngine:
    """Deterministic stand-in for an LLM engine."""
    def generate(self, date, lines):
        return {"headline": f"Headline {date}", "summary": f"{len(lines)} changes.",
                "takeaways": [f"apply {date}"]}


def test_build_digests_is_newest_first_with_grouped_repos_and_totals():
    repo_commits = {
        "alpha": [
            {"sha": "a1", "message": "fix one", "date": "2026-06-20T04:00:00Z"},
            {"sha": "a2", "message": "fix two", "date": "2026-06-20T05:00:00Z"},
        ],
        "beta": [
            {"sha": "b1", "message": "feat x", "date": "2026-06-19T05:00:00Z"},
        ],
    }
    days = daily.build_digests(repo_commits, _FakeEngine())
    assert [d["date"] for d in days] == ["2026-06-20", "2026-06-19"]  # newest first
    d0 = days[0]
    assert d0["headline"] == "Headline 2026-06-20"
    assert d0["total_commits"] == 2
    assert d0["repos"] == [{"name": "alpha", "commits": 2,
                            "messages": ["fix one", "fix two"]}]
    assert d0["takeaways"] == ["apply 2026-06-20"]   # apply-focused detail carried
    assert days[1]["total_commits"] == 1


def test_build_digests_defaults_takeaways_when_engine_omits_them():
    class _Bare:
        def generate(self, date, lines):
            return {"headline": "H", "summary": "S"}  # no takeaways key
    days = daily.build_digests(
        {"alpha": [{"sha": "1", "message": "m", "date": "2026-06-20T00:00:00Z"}]}, _Bare())
    assert days[0]["takeaways"] == []


def test_build_digests_retries_then_falls_back_when_engine_keeps_failing():
    """One bad LLM response must not kill the whole batch."""
    class _Broken:
        calls = 0
        def generate(self, date, lines):
            type(self).calls += 1
            raise ValueError("bad json from model")
    days = daily.build_digests(
        {"alpha": [{"sha": "1", "message": "m", "date": "2026-06-20T00:00:00Z"}]},
        _Broken())
    assert len(days) == 1                       # still produced a day
    assert days[0]["headline"]                  # deterministic fallback headline
    assert days[0]["total_commits"] == 1
    assert _Broken.calls >= 2                   # retried before giving up


def test_build_digests_retry_succeeds_on_a_later_attempt():
    class _FlakyOnce:
        calls = 0
        def generate(self, date, lines):
            type(self).calls += 1
            if type(self).calls == 1:
                raise ValueError("transient")
            return {"headline": "Recovered", "summary": "S", "takeaways": ["t"]}
    days = daily.build_digests(
        {"alpha": [{"sha": "1", "message": "m", "date": "2026-06-20T00:00:00Z"}]},
        _FlakyOnce())
    assert days[0]["headline"] == "Recovered"   # retry won


def test_write_daily_emits_payload(tmp_path):
    out = tmp_path / "data" / "daily.json"
    days = daily.build_digests(
        {"alpha": [{"sha": "a1", "message": "m", "date": "2026-06-20T04:00:00Z"}]},
        _FakeEngine(),
    )
    daily.write_daily(days, str(out))
    payload = json.loads(out.read_text())
    assert payload["count"] == 1
    assert "generated_at" in payload
    assert payload["days"][0]["date"] == "2026-06-20"


# ---------------------------------------------------------------------------
# collect (orchestration over an injected gh client)
# ---------------------------------------------------------------------------

def test_collect_iterates_repos_and_skips_empty():
    class _GH:
        def fetch_repos(self, owner):
            return [{"name": "alpha"}, {"name": "empty"}]
        def fetch_commits(self, owner, repo, since=None):
            return [{"sha": "1", "message": "m", "date": "2026-06-20T00:00:00Z"}] if repo == "alpha" else []
    rc = daily.collect("davidbmar", _GH(), since="2026-06-01")
    assert set(rc) == {"alpha"}            # empty repo dropped
    assert rc["alpha"][0]["sha"] == "1"
