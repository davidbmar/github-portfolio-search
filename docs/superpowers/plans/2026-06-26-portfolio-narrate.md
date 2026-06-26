# Portfolio-Narrate Implementation Plan (v1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn merged PRs across the portfolio into theme-grouped, code-grounded applied tutorials, rendered locally for v1 (`web/learn/<slug>.html` + `/daily/` narrative blurbs).

**Architecture:** Deterministic evidence-backed records are the spine. A `merged_at`-cursor scanner emits one validated `PRRecord` per merged PR (facts extracted by Qwen3.7 from a *bounded* diff). PRRecords are clustered into immutable-slug `ThemeRecord`s via local MiniLM embeddings + a one-shot LLM `attach|create|ignore` decision persisted in a membership ledger. A deterministic maturity score gates which themes get a tutorial. All logic lives in `src/ghps/narrate/` (importable, cron + skill share it); a thin skill wraps `ghps narrate`. Cross-repo publishing is explicitly v2, not in this plan.

**Tech Stack:** Python 3.9+, Click, `requests` (GitHub API), sentence-transformers (`all-MiniLM-L6-v2`), DashScope Qwen3.7 via `DashScopeClient.complete_json`, pytest.

## Global Constraints

- Python 3.9+ compatible (repo floor). Use `from __future__ import annotations`; prefer `list`/`dict`/`tuple` generics under that import.
- **Model: DashScope Qwen3.7** for all LLM steps, via the existing `DashScopeClient` (`src/ghps/docsgen/llm_client.py:80`); never hardcode — read `DASHSCOPE_MODEL` env, default `qwen-plus`. Keep the `LLMClient` Protocol (`complete_json(system, user) -> dict`) as the only LLM seam.
- **Records are validated before any render.** Mirror the fail-closed pattern in `record_gen.py` (`RecordGenerationError`, retry-then-raise).
- **Slugs are immutable.** Once a `ThemeRecord` has a slug, no code path may change it. A force rebuild rebuilds ThemeRecords from PRRecords + ledger and MUST NOT mint new slugs for known themes.
- **State lives in the repo**, not the skill folder: `web/data/narrate/` (`cursor.json`, `pr_records/`, `theme_records/`, `membership.jsonl`).
- Evidence comes from the GitHub PR files API + `merge_commit_sha`, never local branch history (squash/rebase-safe).
- Never write a file named `index.html` into any repo's `docs/html/` (the docs build renames it to `overview.html`, `generate.py:194`).
- TDD: failing test first, minimal impl, frequent commits. No network in unit tests — inject fakes for the GitHub session and the LLM/embedding clients.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/ghps/narrate/__init__.py` | Package marker + public exports |
| `src/ghps/narrate/schema.py` | `PRRecord`, `ThemeRecord` dataclasses, validators, content hashing, slug helpers |
| `src/ghps/narrate/store.py` | Read/write cursor, pr_records, theme_records, membership ledger (atomic JSON) |
| `src/ghps/narrate/scan.py` | Merged-PR scan with `merged_at` cursor + overlap + `seen` set → raw PR dicts |
| `src/ghps/narrate/reduce.py` | Deterministic diff filter + evidence selection; LLM fact extraction → validated `PRRecord` |
| `src/ghps/narrate/cluster.py` | MiniLM embed, cosine retrieval, `attach\|create\|ignore` classify, ledger write |
| `src/ghps/narrate/mature.py` | Maturity score + lifecycle transitions (candidate/mature/published/archived) |
| `src/ghps/narrate/render.py` | `web/learn/<slug>.html` + `/learn/` index + `/daily/` blurb fields |
| `src/ghps/narrate/pipeline.py` | Orchestrate scan→reduce→cluster→mature→render |
| `src/ghps/github_client.py` (modify) | Add `fetch_merged_prs`, `fetch_pr_files` |
| `src/ghps/cli.py` (modify) | Add `ghps narrate` command |
| `~/.claude/skills/portfolio-narrate/SKILL.md` | Thin skill that shells into `ghps narrate` |
| `tests/narrate/test_*.py` | One test module per source module |

---

## Task 1: Schemas, validators, content hashing

**Files:**
- Create: `src/ghps/narrate/__init__.py`
- Create: `src/ghps/narrate/schema.py`
- Test: `tests/narrate/test_schema.py`

**Interfaces:**
- Produces:
  - `files_hash(files: list[dict]) -> str` — stable sha256 over sorted (path, status, adds, dels).
  - `make_slug(title: str) -> str` — kebab-case, alnum+hyphen, deduped hyphens, lowercased.
  - `validate_pr_record(d: dict) -> None` — raises `NarrateValidationError` on missing/empty required keys.
  - `validate_theme_record(d: dict) -> None` — same for ThemeRecord.
  - `PR_REQUIRED: tuple[str, ...]`, `THEME_REQUIRED: tuple[str, ...]`, `THEME_STATES = ("candidate","mature","published","archived")`.
  - `class NarrateValidationError(RuntimeError)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_schema.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: ghps.narrate.schema`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ghps/narrate/__init__.py
"""Portfolio-narrate: PR-grounded applied tutorials."""
```

```python
# src/ghps/narrate/schema.py
from __future__ import annotations

import hashlib
import json
import re

THEME_STATES = ("candidate", "mature", "published", "archived")

PR_REQUIRED = (
    "pr_number", "repo", "merged_at", "title",
    "problem", "approach", "components", "apis_changed",
    "tests_changed", "reusable_pattern", "risks", "files",
)
THEME_REQUIRED = (
    "theme_id", "slug", "title", "status", "repos", "pr_numbers",
    "summary", "narrative",
)


class NarrateValidationError(RuntimeError):
    """Raised when a PRRecord or ThemeRecord fails validation."""


def files_hash(files: list[dict]) -> str:
    norm = sorted(
        (f.get("path", ""), f.get("status", ""), int(f.get("adds", 0)), int(f.get("dels", 0)))
        for f in files
    )
    blob = json.dumps(norm, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def make_slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return re.sub(r"-+", "-", s).strip("-")


def _require(d: dict, keys: tuple[str, ...]) -> None:
    for k in keys:
        if k not in d or d[k] in (None, "", [], {}):
            raise NarrateValidationError(f"missing/empty required field: {k}")


def validate_pr_record(d: dict) -> None:
    _require(d, PR_REQUIRED)


def validate_theme_record(d: dict) -> None:
    _require(d, THEME_REQUIRED)
    if d["status"] not in THEME_STATES:
        raise NarrateValidationError(f"bad status: {d['status']}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_schema.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/__init__.py src/ghps/narrate/schema.py tests/narrate/test_schema.py
git commit -m "feat(narrate): PRRecord/ThemeRecord schemas, validators, content hashing

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 2: State store (cursor, records, ledger)

**Files:**
- Create: `src/ghps/narrate/store.py`
- Test: `tests/narrate/test_store.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class Store` with `__init__(self, root: str | Path)`.
  - `Store.read_cursor(repo: str) -> str | None` / `write_cursor(repo: str, merged_at: str) -> None`.
  - `Store.put_pr(rec: dict) -> None` (keyed `repo/pr_number`) / `get_pr(repo: str, pr_number: int) -> dict | None` / `all_prs() -> list[dict]`.
  - `Store.put_theme(rec: dict) -> None` (keyed `theme_id`) / `all_themes() -> list[dict]` / `get_theme(theme_id: str) -> dict | None`.
  - `Store.ledger_decision(repo: str, pr_number: int) -> dict | None` / `append_ledger(entry: dict) -> None`.
- Writes are atomic (temp file + `os.replace`). Ledger is append-only JSONL.

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_store.py
from ghps.narrate.store import Store

def test_cursor_roundtrip(tmp_path):
    s = Store(tmp_path)
    assert s.read_cursor("riff") is None
    s.write_cursor("riff", "2026-06-20T00:00:00Z")
    assert s.read_cursor("riff") == "2026-06-20T00:00:00Z"

def test_pr_roundtrip_and_key(tmp_path):
    s = Store(tmp_path)
    s.put_pr({"repo": "riff", "pr_number": 12, "title": "x"})
    assert s.get_pr("riff", 12)["title"] == "x"
    assert len(s.all_prs()) == 1

def test_ledger_last_decision_wins(tmp_path):
    s = Store(tmp_path)
    s.append_ledger({"repo": "riff", "pr_number": 3, "theme_id": "t1"})
    s.append_ledger({"repo": "riff", "pr_number": 3, "theme_id": "t2"})
    assert s.ledger_decision("riff", 3)["theme_id"] == "t2"

def test_theme_roundtrip(tmp_path):
    s = Store(tmp_path)
    s.put_theme({"theme_id": "t1", "slug": "a"})
    assert s.get_theme("t1")["slug"] == "a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: ghps.narrate.store`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ghps/narrate/store.py
from __future__ import annotations

import json
import os
from pathlib import Path


class Store:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        (self.root / "pr_records").mkdir(parents=True, exist_ok=True)
        (self.root / "theme_records").mkdir(parents=True, exist_ok=True)
        self._cursor = self.root / "cursor.json"
        self._ledger = self.root / "membership.jsonl"

    def _write_json(self, path: Path, obj) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
        os.replace(tmp, path)

    def read_cursor(self, repo: str) -> str | None:
        if not self._cursor.exists():
            return None
        return json.loads(self._cursor.read_text()).get(repo)

    def write_cursor(self, repo: str, merged_at: str) -> None:
        data = json.loads(self._cursor.read_text()) if self._cursor.exists() else {}
        data[repo] = merged_at
        self._write_json(self._cursor, data)

    def _pr_path(self, repo: str, pr_number: int) -> Path:
        return self.root / "pr_records" / f"{repo}__{pr_number}.json"

    def put_pr(self, rec: dict) -> None:
        self._write_json(self._pr_path(rec["repo"], rec["pr_number"]), rec)

    def get_pr(self, repo: str, pr_number: int) -> dict | None:
        p = self._pr_path(repo, pr_number)
        return json.loads(p.read_text()) if p.exists() else None

    def all_prs(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted((self.root / "pr_records").glob("*.json"))]

    def put_theme(self, rec: dict) -> None:
        self._write_json(self.root / "theme_records" / f"{rec['theme_id']}.json", rec)

    def get_theme(self, theme_id: str) -> dict | None:
        p = self.root / "theme_records" / f"{theme_id}.json"
        return json.loads(p.read_text()) if p.exists() else None

    def all_themes(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted((self.root / "theme_records").glob("*.json"))]

    def append_ledger(self, entry: dict) -> None:
        with self._ledger.open("a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

    def ledger_decision(self, repo: str, pr_number: int) -> dict | None:
        if not self._ledger.exists():
            return None
        found = None
        for line in self._ledger.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("repo") == repo and e.get("pr_number") == pr_number:
                found = e
        return found
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_store.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/store.py tests/narrate/test_store.py
git commit -m "feat(narrate): repo-local state store (cursor, records, membership ledger)

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 3: GitHub merged-PR + PR-files fetchers

**Files:**
- Modify: `src/ghps/github_client.py` (add two functions after `fetch_open_prs`, ~line 460)
- Test: `tests/narrate/test_github_prs.py`

**Interfaces:**
- Consumes: existing `_session()`, `API_BASE` in `github_client.py`.
- Produces:
  - `fetch_merged_prs(owner: str, repo: str, since: str | None = None) -> list[dict]` — returns PRs with `merged_at` not null, sorted ascending by `merged_at`, only those with `merged_at > since` when `since` given. Each dict carries at least `number`, `title`, `body`, `merged_at`, `merge_commit_sha`, `labels` (list of names).
  - `fetch_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]` — `[{path, status, adds, dels, patch}]` from the PR files API.

- [ ] **Step 1: Write the failing test** (inject a fake session via monkeypatch)

```python
# tests/narrate/test_github_prs.py
from ghps import github_client as gc

class _Resp:
    def __init__(self, data): self._data = data; self.status_code = 200; self.headers = {}
    def json(self): return self._data
    def raise_for_status(self): pass

class _FakeSession:
    def __init__(self, routes): self.routes = routes
    def get(self, url, params=None, **kw):
        for frag, data in self.routes.items():
            if frag in url:
                return _Resp(data)
        return _Resp([])

def test_fetch_merged_prs_filters_and_sorts(monkeypatch):
    prs = [
        {"number": 2, "merged_at": "2026-06-21T00:00:00Z", "title": "b", "body": "",
         "merge_commit_sha": "s2", "labels": [{"name": "feat"}]},
        {"number": 1, "merged_at": "2026-06-19T00:00:00Z", "title": "a", "body": "",
         "merge_commit_sha": "s1", "labels": []},
        {"number": 3, "merged_at": None, "title": "open", "body": "",
         "merge_commit_sha": None, "labels": []},
    ]
    monkeypatch.setattr(gc, "_session", lambda: _FakeSession({"/pulls": prs}))
    out = gc.fetch_merged_prs("o", "r", since="2026-06-20T00:00:00Z")
    assert [p["number"] for p in out] == [2]          # #1 too old, #3 not merged
    assert out[0]["labels"] == ["feat"]

def test_fetch_pr_files_shape(monkeypatch):
    files = [{"filename": "a.py", "status": "modified", "additions": 3,
              "deletions": 1, "patch": "@@ -1 +1 @@"}]
    monkeypatch.setattr(gc, "_session", lambda: _FakeSession({"/files": files}))
    out = gc.fetch_pr_files("o", "r", 7)
    assert out[0] == {"path": "a.py", "status": "modified", "adds": 3, "dels": 1, "patch": "@@ -1 +1 @@"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_github_prs.py -v`
Expected: FAIL with `AttributeError: module 'ghps.github_client' has no attribute 'fetch_merged_prs'`

- [ ] **Step 3: Write minimal implementation** (append to `github_client.py`)

```python
def fetch_merged_prs(owner: str, repo: str, since: str | None = None) -> list[dict[str, Any]]:
    """Merged PRs for owner/repo, ascending by merged_at; only newer than `since`."""
    session = _session()
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/pulls",
            params={"state": "closed", "sort": "updated", "direction": "desc",
                    "per_page": 100, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for pr in batch:
            if not pr.get("merged_at"):
                continue
            if since and pr["merged_at"] <= since:
                continue
            out.append({
                "number": pr["number"],
                "title": pr.get("title", ""),
                "body": pr.get("body") or "",
                "merged_at": pr["merged_at"],
                "merge_commit_sha": pr.get("merge_commit_sha"),
                "labels": [l["name"] for l in pr.get("labels", [])],
            })
        if len(batch) < 100:
            break
        page += 1
    out.sort(key=lambda p: p["merged_at"])
    return out


def fetch_pr_files(owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Changed files for a PR: [{path, status, adds, dels, patch}]."""
    session = _session()
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/files",
            params={"per_page": 100, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for f in batch:
            out.append({
                "path": f.get("filename", ""),
                "status": f.get("status", ""),
                "adds": f.get("additions", 0),
                "dels": f.get("deletions", 0),
                "patch": f.get("patch", ""),
            })
        if len(batch) < 100:
            break
        page += 1
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_github_prs.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/github_client.py tests/narrate/test_github_prs.py
git commit -m "feat(narrate): GitHub merged-PR and PR-files fetchers

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 4: Scan — merged_at cursor + overlap + seen set

**Files:**
- Create: `src/ghps/narrate/scan.py`
- Test: `tests/narrate/test_scan.py`

**Interfaces:**
- Consumes: `github_client.fetch_merged_prs`, `Store.read_cursor/write_cursor`.
- Produces:
  - `scan_repo(owner: str, repo: str, store: Store, *, overlap_days: int = 3, fetch=fetch_merged_prs) -> list[dict]` — returns new merged PRs (those whose `pr_number` is not already a stored PRRecord), advances the cursor to the max `merged_at` seen. `fetch` is injectable for tests.
- Rule: query `since = cursor - overlap_days` (re-scan window), then drop any PR already in the store (`store.get_pr`), so late-merged old PRs in the window are caught but nothing is reprocessed.

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_scan.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_scan.py -v`
Expected: FAIL with `ModuleNotFoundError: ghps.narrate.scan`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ghps/narrate/scan.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..github_client import fetch_merged_prs
from .store import Store


def _shift(iso: str | None, days: int) -> str | None:
    if not iso:
        return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")) - timedelta(days=days)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan_repo(owner: str, repo: str, store: Store, *, overlap_days: int = 3, fetch=fetch_merged_prs) -> list[dict]:
    cursor = store.read_cursor(repo)
    since = _shift(cursor, overlap_days)
    candidates = fetch(owner, repo, since=since)
    new: list[dict] = []
    max_merged = cursor
    for pr in candidates:
        max_merged = pr["merged_at"] if (max_merged is None or pr["merged_at"] > max_merged) else max_merged
        if store.get_pr(repo, pr["number"]) is not None:
            continue
        new.append(pr)
    if max_merged:
        store.write_cursor(repo, max_merged)
    return new
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_scan.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/scan.py tests/narrate/test_scan.py
git commit -m "feat(narrate): merged_at-cursor PR scan with overlap window + seen-skip

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 5: Reduce — deterministic diff filter + evidence selection

**Files:**
- Create: `src/ghps/narrate/reduce.py`
- Test: `tests/narrate/test_reduce_filter.py`

**Interfaces:**
- Consumes: nothing (pure functions over file dicts from `fetch_pr_files`).
- Produces:
  - `IGNORE_GLOBS: tuple[str, ...]` — lockfiles, generated, vendored, snapshots, minified, images.
  - `is_signal_file(path: str) -> bool` — False for ignore globs.
  - `select_evidence(files: list[dict], *, max_files: int = 6, max_patch_chars: int = 1500) -> list[dict]` — keeps signal files, ranks tests + public-interface files first, returns `[{path, excerpt}]` with truncated patches.
  - `manifest(files: list[dict]) -> list[dict]` — `[{path, status, adds, dels, lang}]` for ALL files (used for hashing + maturity), where `lang` is derived from extension.

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_reduce_filter.py
from ghps.narrate.reduce import is_signal_file, select_evidence, manifest

def test_ignore_lockfiles_and_generated():
    assert not is_signal_file("package-lock.json")
    assert not is_signal_file("web/data/projects.json")
    assert not is_signal_file("dist/app.min.js")
    assert is_signal_file("src/ghps/daily.py")

def test_select_evidence_prioritizes_tests(tmp_files=None):
    files = [
        {"path": "src/a.py", "status": "modified", "adds": 2, "dels": 0, "patch": "x" * 5000},
        {"path": "tests/test_a.py", "status": "added", "adds": 50, "dels": 0, "patch": "assert"},
        {"path": "package-lock.json", "status": "modified", "adds": 999, "dels": 0, "patch": "noise"},
    ]
    ev = select_evidence(files, max_files=2, max_patch_chars=100)
    paths = [e["path"] for e in ev]
    assert "tests/test_a.py" in paths            # test prioritized
    assert "package-lock.json" not in paths      # ignored
    assert all(len(e["excerpt"]) <= 100 for e in ev)

def test_manifest_includes_all_with_lang():
    files = [{"path": "a.py", "status": "modified", "adds": 1, "dels": 0, "patch": ""}]
    m = manifest(files)
    assert m[0]["lang"] == "python"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_reduce_filter.py -v`
Expected: FAIL with `ModuleNotFoundError: ghps.narrate.reduce`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ghps/narrate/reduce.py
from __future__ import annotations

import fnmatch

IGNORE_GLOBS = (
    "*-lock.json", "*.lock", "package-lock.json", "yarn.lock", "poetry.lock",
    "web/data/*", "dist/*", "build/*", "*.min.js", "*.min.css",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico",
    "*.snap", "vendor/*", "node_modules/*", "*.generated.*",
)
_LANG = {"py": "python", "js": "javascript", "ts": "typescript", "go": "go",
         "rs": "rust", "md": "markdown", "yml": "yaml", "yaml": "yaml",
         "html": "html", "css": "css", "json": "json", "sh": "shell"}


def _lang(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return _LANG.get(ext, ext or "unknown")


def is_signal_file(path: str) -> bool:
    return not any(fnmatch.fnmatch(path, g) for g in IGNORE_GLOBS)


def _is_test(path: str) -> bool:
    return "test" in path.lower()


def _is_public_iface(path: str) -> bool:
    p = path.lower()
    return any(t in p for t in ("__init__.py", "cli.py", "api", "schema", "client", "server"))


def manifest(files: list[dict]) -> list[dict]:
    return [{"path": f["path"], "status": f.get("status", ""),
             "adds": f.get("adds", 0), "dels": f.get("dels", 0),
             "lang": _lang(f["path"])} for f in files]


def select_evidence(files: list[dict], *, max_files: int = 6, max_patch_chars: int = 1500) -> list[dict]:
    signal = [f for f in files if is_signal_file(f["path"])]

    def rank(f):
        return (0 if _is_test(f["path"]) else 1 if _is_public_iface(f["path"]) else 2,
                -(f.get("adds", 0) + f.get("dels", 0)))

    signal.sort(key=rank)
    out = []
    for f in signal[:max_files]:
        out.append({"path": f["path"], "excerpt": (f.get("patch", "") or "")[:max_patch_chars]})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_reduce_filter.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/reduce.py tests/narrate/test_reduce_filter.py
git commit -m "feat(narrate): deterministic diff filter + evidence selection

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 6: Reduce — LLM fact extraction → validated PRRecord

**Files:**
- Modify: `src/ghps/narrate/reduce.py` (add `build_pr_messages`, `build_pr_record`)
- Test: `tests/narrate/test_reduce_llm.py`

**Interfaces:**
- Consumes: `select_evidence`, `manifest`, `files_hash`, `validate_pr_record`, an `LLMClient` (`complete_json(system, user) -> dict`).
- Produces:
  - `PR_FACT_SYSTEM: str` — prompt instructing JSON-only output with keys `problem, approach, components, apis_changed, tests_changed, reusable_pattern, risks`.
  - `build_pr_messages(pr: dict, evidence: list[dict]) -> tuple[str, str]`.
  - `build_pr_record(pr: dict, files: list[dict], client, *, model: str) -> dict` — validated PRRecord; raises `NarrateValidationError` after retries.

- [ ] **Step 1: Write the failing test** (inject a fake client)

```python
# tests/narrate/test_reduce_llm.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_reduce_llm.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_pr_record'`

- [ ] **Step 3: Write minimal implementation** (append to `reduce.py`)

```python
from .schema import files_hash, validate_pr_record, NarrateValidationError

PR_FACT_SYSTEM = (
    "You are a senior engineer extracting REUSABLE facts from one merged pull request. "
    "Output ONE JSON object with EXACTLY these keys: problem (string), approach (string), "
    "components (array of short strings), apis_changed (array), tests_changed (array), "
    "reusable_pattern (boolean: does this PR introduce a pattern another dev could reuse?), "
    "risks (array). Ground every field in the diff; do not invent. No markdown, JSON only."
)
_LLM_KEYS = ("problem", "approach", "components", "apis_changed",
             "tests_changed", "reusable_pattern", "risks")


def build_pr_messages(pr: dict, evidence: list[dict]) -> tuple[str, str]:
    ev = "\n\n".join(f"--- {e['path']} ---\n{e['excerpt']}" for e in evidence)
    user = (f"PR #{pr['number']}: {pr.get('title','')}\n"
            f"Labels: {', '.join(pr.get('labels', [])) or '(none)'}\n"
            f"Description:\n{(pr.get('body') or '')[:2000]}\n\n"
            f"Changed-file evidence (truncated):\n{ev or '(none)'}\n")
    return PR_FACT_SYSTEM, user


def build_pr_record(pr: dict, files: list[dict], client, *, model: str) -> dict:
    evidence = select_evidence(files)
    system, user = build_pr_messages(pr, evidence)
    last = None
    for _ in range(2):
        try:
            llm = client.complete_json(system, user)
            part = {k: llm[k] for k in _LLM_KEYS if k in llm}
            rec = {
                "pr_number": pr["number"], "repo": pr.get("repo", pr.get("repo_name", "")),
                "merged_at": pr["merged_at"], "title": pr.get("title", ""),
                "body": (pr.get("body") or "")[:2000], "labels": pr.get("labels", []),
                "merge_commit_sha": pr.get("merge_commit_sha"),
                "files": manifest(files), "files_hash": files_hash(manifest(files)),
                "evidence": evidence, "model": model,
                **part,
            }
            validate_pr_record(rec)
            return rec
        except (KeyError, NarrateValidationError) as e:
            last = e
    raise NarrateValidationError(f"PR #{pr['number']}: {last}")
```

Note: `repo` must be set on the `pr` dict by the caller — the pipeline (Task 11) injects `pr["repo"] = repo` before calling `build_pr_record`, and the Step 1 tests above already include `"repo": "riff"`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_reduce_llm.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/reduce.py tests/narrate/test_reduce_llm.py
git commit -m "feat(narrate): LLM fact extraction into validated PRRecord (Qwen3.7)

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 7: Cluster — embedding + cosine retrieval

**Files:**
- Create: `src/ghps/narrate/cluster.py`
- Test: `tests/narrate/test_cluster_retrieve.py`

**Interfaces:**
- Consumes: `EmbeddingPipeline.embed_text` (normalized vectors → cosine == dot product).
- Produces:
  - `pr_embed_text(rec: dict) -> str` — concatenation of title + problem + approach + components + apis.
  - `cosine(a: list[float], b: list[float]) -> float`.
  - `retrieve(vec: list[float], themes: list[dict], *, top: int = 5) -> list[tuple[dict, float]]` — themes carry a stored `embedding`; returns top-N by cosine desc.
  - `ATTACH_HI = 0.78`, `ASK_LO = 0.62`.

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_cluster_retrieve.py
from ghps.narrate.cluster import cosine, retrieve, pr_embed_text, ATTACH_HI, ASK_LO

def test_cosine_identity():
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9
    assert abs(cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9

def test_retrieve_ranks_by_cosine():
    themes = [
        {"theme_id": "a", "embedding": [1.0, 0.0]},
        {"theme_id": "b", "embedding": [0.0, 1.0]},
    ]
    out = retrieve([0.9, 0.1], themes, top=2)
    assert out[0][0]["theme_id"] == "a" and out[0][1] > out[1][1]

def test_thresholds_ordered():
    assert ATTACH_HI > ASK_LO

def test_pr_embed_text_includes_problem():
    txt = pr_embed_text({"title": "T", "problem": "P", "approach": "A",
                         "components": ["c"], "apis_changed": ["x"]})
    assert "P" in txt and "T" in txt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_cluster_retrieve.py -v`
Expected: FAIL with `ModuleNotFoundError: ghps.narrate.cluster`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ghps/narrate/cluster.py
from __future__ import annotations

import math

ATTACH_HI = 0.78
ASK_LO = 0.62


def pr_embed_text(rec: dict) -> str:
    parts = [rec.get("title", ""), rec.get("problem", ""), rec.get("approach", "")]
    parts += list(rec.get("components", [])) + list(rec.get("apis_changed", []))
    return " ".join(p for p in parts if p)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def retrieve(vec: list[float], themes: list[dict], *, top: int = 5) -> list[tuple[dict, float]]:
    scored = [(t, cosine(vec, t["embedding"])) for t in themes if t.get("embedding")]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_cluster_retrieve.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/cluster.py tests/narrate/test_cluster_retrieve.py
git commit -m "feat(narrate): MiniLM cosine retrieval for theme candidates

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 8: Cluster — classify attach|create|ignore + immutable slug + ledger

**Files:**
- Modify: `src/ghps/narrate/cluster.py` (add `classify_pr`)
- Test: `tests/narrate/test_cluster_classify.py`

**Interfaces:**
- Consumes: `retrieve`, `ATTACH_HI`, `ASK_LO`, `Store` (ledger + themes), `make_slug`, an `LLMClient`.
- Produces:
  - `classify_pr(rec: dict, vec: list[float], store: Store, client, *, model: str, reclassify: bool = False) -> dict` — returns the decision dict `{repo, pr_number, theme_id|None, action, score}` AND writes it to the ledger + updates/creates the ThemeRecord membership. If a prior ledger decision exists and not `reclassify`, returns it unchanged (idempotent). Cosine ≥ ATTACH_HI → attach to top theme without asking the LLM; between ASK_LO and ATTACH_HI → ask LLM `attach|create|ignore`; below ASK_LO → LLM may only `create|ignore`. New themes get an immutable slug from the LLM-proposed title via `make_slug`, deduped against existing slugs.

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_cluster_classify.py
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
    assert 1 in store.get_theme("t1")["pr_numbers"]

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_cluster_classify.py -v`
Expected: FAIL with `ImportError: cannot import name 'classify_pr'`

- [ ] **Step 3: Write minimal implementation** (append to `cluster.py`)

```python
from .schema import make_slug
from .store import Store

CLASSIFY_SYSTEM = (
    "Decide how a pull request relates to existing work THEMES. "
    "Output ONE JSON object: {\"action\": \"attach\"|\"create\"|\"ignore\", "
    "\"theme_id\": <id or null>, \"title\": <new theme title if create>}. "
    "attach only if the PR clearly extends an existing theme; ignore chores/deps."
)


def _unique_slug(base: str, store: Store) -> str:
    existing = {t["slug"] for t in store.all_themes()}
    slug, i = base, 2
    while slug in existing:
        slug, i = f"{base}-{i}", i + 1
    return slug


def _new_theme_id(store: Store) -> str:
    return f"t{len(store.all_themes()) + 1}"


def _attach(store: Store, theme_id: str, rec: dict) -> None:
    t = store.get_theme(theme_id)
    if rec["pr_number"] not in t["pr_numbers"]:
        t["pr_numbers"].append(rec["pr_number"])
    if rec["repo"] not in t["repos"]:
        t["repos"].append(rec["repo"])
    t["last_activity_at"] = rec["merged_at"] if "merged_at" in rec else t.get("last_activity_at")
    store.put_theme(t)


def classify_pr(rec, vec, store, client, *, model, reclassify=False) -> dict:
    prior = store.ledger_decision(rec["repo"], rec["pr_number"])
    if prior and not reclassify:
        return prior

    cands = retrieve(vec, store.all_themes(), top=5)
    top_score = cands[0][1] if cands else 0.0

    if cands and top_score >= ATTACH_HI:
        action, theme_id = "attach", cands[0][0]["theme_id"]
    else:
        allow_attach = ASK_LO <= top_score < ATTACH_HI
        ask = client.complete_json(
            CLASSIFY_SYSTEM,
            f"PR: {rec.get('title','')}\nCandidates: "
            f"{[(t['theme_id'], t.get('title','')) for t, _ in cands] if allow_attach else '(none eligible)'}",
        )
        action = ask.get("action", "ignore")
        if action == "attach" and not allow_attach:
            action = "create"
        if action == "attach":
            theme_id = ask.get("theme_id") or (cands[0][0]["theme_id"] if cands else None)
            if not theme_id:
                action = "create"
        if action == "create":
            theme_id = _new_theme_id(store)
            slug = _unique_slug(make_slug(ask.get("title") or rec.get("title", "theme")), store)
            store.put_theme({
                "theme_id": theme_id, "slug": slug, "title": ask.get("title") or rec.get("title", ""),
                "aliases": [], "status": "candidate", "repos": [], "pr_numbers": [],
                "embedding": vec, "candidate_since": rec.get("merged_at"),
                "last_activity_at": rec.get("merged_at"),
            })
        elif action == "ignore":
            theme_id = None

    if action in ("attach", "create"):
        _attach(store, theme_id, rec)

    decision = {"repo": rec["repo"], "pr_number": rec["pr_number"],
                "theme_id": theme_id, "action": action, "score": top_score,
                "classifier_model": model}
    store.append_ledger(decision)
    return decision
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_cluster_classify.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/cluster.py tests/narrate/test_cluster_classify.py
git commit -m "feat(narrate): attach|create|ignore classifier with immutable slug + ledger

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 9: Mature — scoring + lifecycle transitions

**Files:**
- Create: `src/ghps/narrate/mature.py`
- Test: `tests/narrate/test_mature.py`

**Interfaces:**
- Consumes: `Store.all_prs`, `Store.all_themes`, `Store.put_theme`.
- Produces:
  - `score_theme(theme: dict, prs: list[dict]) -> tuple[int, str]` — `(score, reason)` using the spec formula: `+2` per PR (cap 6), `+2` any tests_changed, `+2` any apis_changed, `+1` docs/readme touched, `+2` any reusable_pattern, `-3` chore/deps-only.
  - `apply_lifecycle(store: Store, *, mature_at: int = 7) -> list[dict]` — recomputes score for each theme, transitions `candidate→mature` at `>= mature_at`, writes `maturity_score`/`maturity_reason`, returns themes now mature-or-better.

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_mature.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_mature.py -v`
Expected: FAIL with `ModuleNotFoundError: ghps.narrate.mature`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ghps/narrate/mature.py
from __future__ import annotations

from .store import Store


def score_theme(theme: dict, prs: list[dict]) -> tuple[int, str]:
    members = [p for p in prs if p["pr_number"] in theme.get("pr_numbers", [])]
    reasons, score = [], 0
    pr_pts = min(len(members) * 2, 6)
    score += pr_pts; reasons.append(f"{len(members)} PRs (+{pr_pts})")
    if any(p.get("tests_changed") for p in members):
        score += 2; reasons.append("tests (+2)")
    if any(p.get("apis_changed") for p in members):
        score += 2; reasons.append("public API (+2)")
    if any(any(f.get("path", "").lower().endswith((".md", "readme"))
               for f in p.get("files", [])) for p in members):
        score += 1; reasons.append("docs (+1)")
    if any(p.get("reusable_pattern") for p in members):
        score += 2; reasons.append("reusable pattern (+2)")
    if members and all(
        any(l in ("chore", "deps", "dependencies") for l in p.get("labels", [])) for p in members
    ):
        score -= 3; reasons.append("chore/deps only (-3)")
    return score, ", ".join(reasons)


def apply_lifecycle(store: Store, *, mature_at: int = 7) -> list[dict]:
    prs = store.all_prs()
    matured = []
    for theme in store.all_themes():
        score, reason = score_theme(theme, prs)
        theme["maturity_score"] = score
        theme["maturity_reason"] = reason
        if theme["status"] == "candidate" and score >= mature_at:
            theme["status"] = "mature"
        store.put_theme(theme)
        if theme["status"] in ("mature", "published"):
            matured.append(theme)
    return matured
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_mature.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/mature.py tests/narrate/test_mature.py
git commit -m "feat(narrate): maturity scoring + candidate->mature lifecycle

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 10: Render — tutorial HTML + /learn/ index (local v1)

**Files:**
- Create: `src/ghps/narrate/render.py`
- Test: `tests/narrate/test_render.py`

**Interfaces:**
- Consumes: `Store.all_prs`, a `ThemeRecord` with tutorial prose fields, an `LLMClient`.
- Produces:
  - `TUTORIAL_SYSTEM: str` — prompt for `summary, narrative, principles[], patterns[], applied_examples[], pitfalls[]` JSON.
  - `write_tutorial_prose(theme: dict, prs: list[dict], client, *, model: str) -> dict` — fills + validates the prose fields on the theme (raises `NarrateValidationError` if invalid).
  - `render_learn_html(theme: dict) -> str` — full HTML page; all prose HTML-escaped (reuse the escaping discipline from `render.py`).
  - `write_learn_pages(themes: list[dict], out_dir: str | Path) -> list[str]` — writes `out_dir/<slug>.html` + `out_dir/index.html`; returns written paths. Never writes a file literally named after a repo's `index.html` in another repo (v1 stays inside `web/learn/`).

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_render.py
from pathlib import Path
from ghps.narrate.render import write_tutorial_prose, render_learn_html, write_learn_pages

class _Client:
    def complete_json(self, system, user):
        return {"summary": "S", "narrative": "<b>N</b>", "principles": ["p1"],
                "patterns": ["pat"], "applied_examples": ["ex"], "pitfalls": ["pit"]}

def _theme():
    return {"theme_id": "t1", "slug": "llm-judge-routing", "title": "LLM Judge Routing",
            "status": "mature", "repos": ["riff"], "pr_numbers": [1]}

def test_write_tutorial_prose_fills_fields():
    t = write_tutorial_prose(_theme(), [], _Client(), model="qwen3.7-plus")
    assert t["summary"] == "S" and t["principles"] == ["p1"]

def test_render_escapes_html():
    t = _theme(); t.update({"summary": "S", "narrative": "<script>x</script>",
                            "principles": [], "patterns": [], "applied_examples": [], "pitfalls": []})
    html = render_learn_html(t)
    assert "<script>x</script>" not in html and "&lt;script&gt;" in html

def test_write_learn_pages_creates_index(tmp_path):
    t = _theme(); t.update({"summary": "S", "narrative": "N", "principles": [],
                            "patterns": [], "applied_examples": [], "pitfalls": []})
    paths = write_learn_pages([t], tmp_path)
    assert (Path(tmp_path) / "llm-judge-routing.html").exists()
    assert (Path(tmp_path) / "index.html").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: ghps.narrate.render`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ghps/narrate/render.py
from __future__ import annotations

import html
from pathlib import Path

from .schema import NarrateValidationError

TUTORIAL_SYSTEM = (
    "You are writing an APPLIED TUTORIAL (think a readable AWS applied-architecture blog) "
    "about a body of related work, for a developer who wants to learn the principles and reuse them. "
    "Output ONE JSON object: summary (string), narrative (string: what was built and why, no raw code "
    "dumps), principles (array), patterns (array), applied_examples (array: concrete ways to apply this), "
    "pitfalls (array). Ground everything in the provided PR facts. No marketing. JSON only."
)
_PROSE_KEYS = ("summary", "narrative", "principles", "patterns", "applied_examples", "pitfalls")


def write_tutorial_prose(theme: dict, prs: list[dict], client, *, model: str) -> dict:
    members = [p for p in prs if p["pr_number"] in theme.get("pr_numbers", [])]
    facts = "\n".join(
        f"- PR#{p['pr_number']}: {p.get('problem','')} | approach: {p.get('approach','')} | "
        f"pattern: {p.get('reusable_pattern')}" for p in members
    )
    user = f"Theme: {theme.get('title','')}\nRepos: {', '.join(theme.get('repos', []))}\nPR facts:\n{facts}"
    llm = client.complete_json(TUTORIAL_SYSTEM, user)
    for k in _PROSE_KEYS:
        if k not in llm:
            raise NarrateValidationError(f"tutorial missing field: {k}")
        theme[k] = llm[k]
    theme["model"] = model
    return theme


def _ul(items) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(str(i))}</li>" for i in items) + "</ul>" if items else ""


def render_learn_html(theme: dict) -> str:
    t = html.escape(theme.get("title", ""))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{t} — Learn</title></head><body>
<main><h1>{t}</h1>
<p class="summary">{html.escape(theme.get('summary',''))}</p>
<section><h2>What was built &amp; why</h2><p>{html.escape(theme.get('narrative',''))}</p></section>
<section><h2>Principles</h2>{_ul(theme.get('principles', []))}</section>
<section><h2>Patterns</h2>{_ul(theme.get('patterns', []))}</section>
<section><h2>How to apply</h2>{_ul(theme.get('applied_examples', []))}</section>
<section><h2>Pitfalls</h2>{_ul(theme.get('pitfalls', []))}</section>
<footer>Repos: {html.escape(', '.join(theme.get('repos', [])))}</footer>
</main></body></html>"""


def write_learn_pages(themes: list[dict], out_dir: str | Path) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    cards = []
    for t in themes:
        p = out / f"{t['slug']}.html"
        p.write_text(render_learn_html(t))
        written.append(str(p))
        cards.append(f'<li><a href="{t["slug"]}.html">{html.escape(t.get("title",""))}</a> '
                     f'— {html.escape(t.get("summary",""))}</li>')
    idx = out / "index.html"
    idx.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>Learn</title></head>"
                   f"<body><h1>Learn</h1><ul>{''.join(cards)}</ul></body></html>")
    written.append(str(idx))
    return written
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_render.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/render.py tests/narrate/test_render.py
git commit -m "feat(narrate): tutorial prose generation + escaped /learn/ HTML pages

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 11: Pipeline orchestration

**Files:**
- Create: `src/ghps/narrate/pipeline.py`
- Test: `tests/narrate/test_pipeline.py`

**Interfaces:**
- Consumes: everything above + `EmbeddingPipeline`, an `LLMClient`, `github_client.fetch_pr_files`.
- Produces:
  - `run(owner: str, repos: list[str], store: Store, client, embedder, out_dir, *, model: str, fetch_files=fetch_pr_files, scan_fn=scan_repo) -> dict` — runs scan→reduce→cluster→mature→render for each repo; returns `{"prs": n, "themes_matured": m, "pages": [...]}`. Injectable seams keep it unit-testable with fakes.

- [ ] **Step 1: Write the failing test**

```python
# tests/narrate/test_pipeline.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: ghps.narrate.pipeline`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ghps/narrate/pipeline.py
from __future__ import annotations

from ..github_client import fetch_pr_files
from .cluster import classify_pr, pr_embed_text
from .mature import apply_lifecycle
from .reduce import build_pr_record
from .render import write_learn_pages, write_tutorial_prose
from .scan import scan_repo


def run(owner, repos, store, client, embedder, out_dir, *, model,
        fetch_files=fetch_pr_files, scan_fn=scan_repo) -> dict:
    pr_count = 0
    for repo in repos:
        for pr in scan_fn(owner, repo, store):
            pr["repo"] = repo
            files = fetch_files(owner, repo, pr["number"])
            rec = build_pr_record(pr, files, client, model=model)
            store.put_pr(rec)
            pr_count += 1
            vec = embedder.embed_text(pr_embed_text(rec))
            classify_pr(rec, vec, store, client, model=model)

    matured = apply_lifecycle(store)
    for theme in matured:
        write_tutorial_prose(theme, store.all_prs(), client, model=model)
        store.put_theme(theme)
    pages = write_learn_pages(matured, out_dir) if matured else []
    return {"prs": pr_count, "themes_matured": len(matured), "pages": pages}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_pipeline.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/narrate/pipeline.py tests/narrate/test_pipeline.py
git commit -m "feat(narrate): end-to-end pipeline orchestration (scan->render)

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 12: CLI command `ghps narrate`

**Files:**
- Modify: `src/ghps/cli.py` (add command after `daily`, ~line 381)
- Test: `tests/narrate/test_cli.py`

**Interfaces:**
- Consumes: `pipeline.run`, `Store`, `DashScopeClient`, `EmbeddingPipeline`.
- Produces: `ghps narrate --owner davidbmar --repos riff,github-portfolio-search --out web/learn --state web/data/narrate` — wires real clients and prints the run summary. Uses the same provider-selection helper `gen-docs` uses (default DashScope/Qwen).

- [ ] **Step 1: Write the failing test** (CliRunner with monkeypatched `run`)

```python
# tests/narrate/test_cli.py
from click.testing import CliRunner
from ghps import cli
from ghps.narrate import pipeline

def test_narrate_invokes_pipeline(monkeypatch, tmp_path):
    captured = {}
    def fake_run(owner, repos, store, client, embedder, out_dir, **kw):
        captured.update(owner=owner, repos=repos)
        return {"prs": 2, "themes_matured": 1, "pages": ["x/index.html"]}
    monkeypatch.setattr(pipeline, "run", fake_run)
    # Avoid loading heavy clients:
    monkeypatch.setattr(cli, "_narrate_client", lambda provider, model: object(), raising=False)
    monkeypatch.setattr(cli, "_narrate_embedder", lambda: object(), raising=False)
    res = CliRunner().invoke(cli.main, ["narrate", "--owner", "davidbmar",
                                        "--repos", "riff", "--out", str(tmp_path),
                                        "--state", str(tmp_path / "s")])
    assert res.exit_code == 0
    assert captured["owner"] == "davidbmar" and captured["repos"] == ["riff"]
    assert "themes_matured" in res.output or "1" in res.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/narrate/test_cli.py -v`
Expected: FAIL with `No such command 'narrate'`

- [ ] **Step 3: Write minimal implementation** (add to `cli.py`)

```python
@main.command(name="narrate")
@click.option("--owner", default="davidbmar", help="GitHub owner/org.")
@click.option("--repos", required=True, help="Comma-separated repo slugs.")
@click.option("--out", "out_dir", default="web/learn", help="Output dir for /learn pages.")
@click.option("--state", "state_dir", default="web/data/narrate", help="State dir.")
@click.option("--provider", default=None, help="LLM provider (dashscope|anthropic).")
@click.option("--model", default=None, help="Override model id.")
def narrate(owner, repos, out_dir, state_dir, provider, model):
    """Generate theme-grouped applied tutorials from merged PRs."""
    from .narrate import pipeline
    from .narrate.store import Store
    repo_list = [r.strip() for r in repos.split(",") if r.strip()]
    client = _narrate_client(provider, model)
    embedder = _narrate_embedder()
    eff_model = model or os.environ.get("DASHSCOPE_MODEL", "qwen-plus")
    summary = pipeline.run(owner, repo_list, Store(state_dir), client, embedder,
                           out_dir, model=eff_model)
    click.echo(f"narrate: {summary['prs']} PRs, "
               f"{summary['themes_matured']} themes matured, "
               f"{len(summary['pages'])} pages written")


def _narrate_client(provider, model):
    from .docsgen.llm_client import DashScopeClient, AnthropicClient
    if provider == "anthropic":
        return AnthropicClient()
    return DashScopeClient()


def _narrate_embedder():
    from .embeddings import EmbeddingPipeline
    return EmbeddingPipeline()
```

(Ensure `import os` exists at the top of `cli.py`; it does — verify before running.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/narrate/test_cli.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Run the full narrate suite + lint, then commit**

```bash
.venv/bin/python -m pytest tests/narrate/ -v
make lint
git add src/ghps/cli.py tests/narrate/test_cli.py
git commit -m "feat(narrate): ghps narrate CLI command

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Task 13: Claude Code skill wrapper

**Files:**
- Create: `~/.claude/skills/portfolio-narrate/SKILL.md`
- Test: manual (skill is a thin shell-out; no pytest)

**Interfaces:**
- Consumes: `ghps narrate` CLI.
- Produces: an installable skill that, on invocation, runs the scan over recent pushes and reports matured themes + written pages. Cross-machine install = copy this dir into each `~/.claude/skills/`.

- [ ] **Step 1: Write the skill file**

```markdown
---
name: portfolio-narrate
description: Scan recent merged PRs across the portfolio, cluster them into themes, and generate applied-tutorial Learn pages. Use when asked to "narrate the portfolio", "update the daily deep-dives", or "generate learn pages".
---

# Portfolio Narrate

Generate theme-grouped, code-grounded applied tutorials from merged PRs.

## Steps

1. Confirm you are in `~/src/github-portfolio-search` (or cd there):
   `cd ~/src/github-portfolio-search`
2. Ensure the venv + DashScope env are present:
   `test -d .venv && grep -q DASHSCOPE_API_KEY .env && echo ok`
3. Run the narrator over the repos of interest (default: all recently-pushed):
   `.venv/bin/python -m ghps narrate --owner davidbmar --repos riff,github-portfolio-search --out web/learn --state web/data/narrate`
4. Report the printed summary (PRs processed, themes matured, pages written).
5. Preview a page locally: open `web/learn/index.html`.
6. To publish, deploy `web/` via the existing pipeline (`make deploy` or the gen-docs workflow). Do NOT hand-edit generated pages.

## Notes
- Records + ledger live in `web/data/narrate/`. Re-runs are idempotent (membership ledger); pass `--reclassify` only to deliberately re-cluster.
- v1 renders locally to `web/learn/`. Cross-repo `docs/html` publishing is a separate (v2) step — do not attempt it from this skill yet.
```

- [ ] **Step 2: Verify the skill loads**

Run: `ls ~/.claude/skills/portfolio-narrate/SKILL.md && head -5 ~/.claude/skills/portfolio-narrate/SKILL.md`
Expected: prints frontmatter.

- [ ] **Step 3: Commit (project-side copy for version control)**

Also keep a tracked copy in-repo so it is reviewable and installable:

```bash
mkdir -p skills/portfolio-narrate
cp ~/.claude/skills/portfolio-narrate/SKILL.md skills/portfolio-narrate/SKILL.md
git add skills/portfolio-narrate/SKILL.md
git commit -m "feat(narrate): portfolio-narrate Claude Code skill wrapper

Session: S-2026-06-26-0000-portfolio-narrate-design"
```

---

## Final verification

- [ ] Run the whole suite: `.venv/bin/python -m pytest tests/narrate/ -v` → all green.
- [ ] `make lint` clean.
- [ ] Live smoke (network, real Qwen3.7): `.venv/bin/python -m ghps narrate --owner davidbmar --repos riff --out web/learn --state /tmp/narrate-smoke` → produces at least one PRRecord; inspect `/tmp/narrate-smoke/pr_records/`.
- [ ] Re-run smoke with the same state dir → byte-stable theme identity (no new slugs, no duplicate themes). This is the bet-proving check.
- [ ] Open `web/learn/index.html` and read one tutorial: does it read like an applied walk-through, not a changelog? If thin, tune `TUTORIAL_SYSTEM` / `PR_FACT_SYSTEM` prompts (cheap, no architecture change).

## Deferred to v2 (not in this plan)

- Cross-repo publishing: commit/push `learn-<slug>.html` into source repos' `docs/html/`, behind the preflight gates in the spec, so nightly `gen-docs fetch_html_docs` republishes to davidbmar.com.
- `/daily/` blurb enrichment + per-project page section (render path c).
- Multi-model panel (codex/gemini/agy) as a pluggable verifier role.
- Scheduled stale/archive lifecycle pass + CI wiring in `gen-docs.yml`.
