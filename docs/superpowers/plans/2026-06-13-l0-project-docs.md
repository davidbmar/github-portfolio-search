# L0 — AI-Generated Project Docs (Self-Documenting Portfolio) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate one rich, browser-rendered, machine-readable HTML doc per GitHub repo (architecture + sequence diagrams, prose sections, typed metadata, repo-hygiene panel), published to davidbmar.com via the existing S3/CloudFront pipeline.

**Architecture:** A new `ghps.docsgen` subpackage pulls per-repo context from the GitHub API, calls an LLM through a provider-agnostic `LLMClient` seam (DashScope/Qwen for v1, Anthropic as a cost/quality dial), and emits a schema-validated **structured record** per repo (`projects/<slug>.record.json`). A pure-Python renderer turns each record into a self-contained HTML page (`web/projects/<slug>.html`) with an embedded JSON island + JSON-LD; an aggregator rolls all records into `web/data/projects.json` for future L2/L3 consumers. One generation pass, two readers (humans + machines).

**Tech Stack:** Python 3.9+ (`from __future__ import annotations` everywhere), `requests` (existing dep) for GitHub + LLM HTTP, `click` (existing) for the CLI command, pure stdlib for schema validation and HTML rendering (no Jinja, no LLM SDKs), `pytest` with `unittest.mock` for tests, Mermaid.js via CDN for client-side diagram rendering.

---

## Design decisions locked from the spec

- **Storage (v1):** records are generated & stored centrally in *this* repo (Approach B) — `projects/<slug>.record.json`, version-controlled. Zero blast radius on the 137 source repos.
- **Template over raw HTML:** the LLM fills a structured record; a fixed renderer produces HTML. Consistency + reliable machine-readability at 137 repos.
- **Provider-agnostic, zero new deps:** `LLMClient` protocol with `DashScopeClient` and `AnthropicClient`, both built on `requests`. v1 uses the existing Alibaba Qwen (DashScope) key.
- **Thin flag:** forks/archived/stubs get an entry marked `thin: true` (minimal token spend) rather than hallucinated depth — protects the future reuse graph.
- **Hygiene panel:** derived from the same GitHub calls — branches ahead of default + open PRs. GitHub API cannot see local uncommitted state (out of scope v1).

## File structure (what each new/modified file is responsible for)

**New (source):**
- `src/ghps/docsgen/__init__.py` — subpackage marker.
- `src/ghps/docsgen/schema.py` — record schema field lists + `validate_record(record) -> list[str]` (returns human-readable errors; empty list = valid).
- `src/ghps/docsgen/hygiene.py` — `derive_todos(branch_status, open_prs) -> list[dict]`, pure function.
- `src/ghps/docsgen/context.py` — `RepoContext` dataclass + `build_context(repo_meta, *, gh=github_client) -> RepoContext`, assembles everything one repo's generation needs.
- `src/ghps/docsgen/llm_client.py` — `LLMClient` protocol, `DashScopeClient`, `AnthropicClient`, `get_client(provider=None) -> LLMClient` factory.
- `src/ghps/docsgen/record_gen.py` — `build_messages(ctx) -> tuple[str, str]`, `generate_record(ctx, client, *, model=None) -> dict` (LLM call + validate + retry + provenance/hygiene/thin fill).
- `src/ghps/docsgen/render.py` — `render_page(record) -> str` (full HTML doc with JSON island, JSON-LD, both Mermaid blocks, hygiene panel).
- `src/ghps/docsgen/aggregate.py` — `aggregate_records(records_dir, output_path) -> dict`.
- `src/ghps/docsgen/generate.py` — orchestrator: `generate_one(...)`, `generate_all(...)`.

**New (tests):**
- `tests/test_docsgen_schema.py`, `tests/test_docsgen_hygiene.py`, `tests/test_docsgen_context.py`, `tests/test_docsgen_llm_client.py`, `tests/test_docsgen_record_gen.py`, `tests/test_docsgen_render.py`, `tests/test_docsgen_aggregate.py`.

**Modified:**
- `src/ghps/github_client.py` — add `fetch_branches`, `compare_commits`, `fetch_open_prs`.
- `tests/test_github_client.py` — add test classes for the three new functions.
- `src/ghps/cli.py` — add `gen-docs` command.
- `Makefile` — add `gen-docs` target.
- `.gitignore` — ensure `.env` ignored (verify; add if missing).
- `.env.example` (create) — document `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`, `DASHSCOPE_MODEL`, `LLM_PROVIDER`.

**Build order:** schema → hygiene → github_client extensions → context → llm_client → record_gen → render → aggregate → orchestrator+CLI → guinea-pig run+deploy. Each task is bottom-up and independently testable.

---

## Task 1: Record schema + validator

**Files:**
- Create: `src/ghps/docsgen/__init__.py`
- Create: `src/ghps/docsgen/schema.py`
- Test: `tests/test_docsgen_schema.py`

- [ ] **Step 1: Create the subpackage marker**

Create `src/ghps/docsgen/__init__.py`:

```python
"""L0 — AI-generated, machine-readable project docs (self-documenting portfolio)."""
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_docsgen_schema.py`:

```python
"""Unit tests for the L0 record schema validator."""

from __future__ import annotations

from ghps.docsgen import schema


def _valid_record() -> dict:
    return {
        "slug": "demo",
        "title": "Demo Project",
        "repo_url": "https://github.com/user/demo",
        "visibility": "public",
        "status": "shipped",
        "thin": False,
        "one_liner": "A demo.",
        "what_it_is": "It is a demo.",
        "how_its_built": "With Python.",
        "how_to_apply": "Copy the pattern.",
        "diagram_architecture": "flowchart LR; A-->B",
        "diagram_sequence": "sequenceDiagram; A->>B: hi",
        "capabilities": ["demoing"],
        "components": ["thing"],
        "tech": ["python"],
        "depends_on": ["requests"],
        "integrates_with": [],
        "patterns": ["adapter"],
        "reuse_tags": ["demo-tag"],
        "todos": [],
        "generated_at": "2026-06-13T00:00:00Z",
        "source_commit": "abc1234",
        "model": "qwen-plus",
    }


def test_valid_record_has_no_errors():
    assert schema.validate_record(_valid_record()) == []


def test_missing_required_string_is_reported():
    rec = _valid_record()
    del rec["what_it_is"]
    errors = schema.validate_record(rec)
    assert any("what_it_is" in e for e in errors)


def test_wrong_type_for_list_field_is_reported():
    rec = _valid_record()
    rec["capabilities"] = "not a list"
    errors = schema.validate_record(rec)
    assert any("capabilities" in e for e in errors)


def test_bad_enum_value_is_reported():
    rec = _valid_record()
    rec["status"] = "launched"  # not in idea|building|shipped
    errors = schema.validate_record(rec)
    assert any("status" in e for e in errors)


def test_thin_must_be_bool():
    rec = _valid_record()
    rec["thin"] = "yes"
    errors = schema.validate_record(rec)
    assert any("thin" in e for e in errors)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_docsgen_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.docsgen.schema'`

- [ ] **Step 4: Write minimal implementation**

Create `src/ghps/docsgen/schema.py`:

```python
"""Schema definition + validator for the L0 structured record.

The record is the single source of truth: the renderer draws a page from it
and the aggregator feeds it to L2/L3. Validation is hand-rolled (no jsonschema
dependency) and returns a list of human-readable error strings — an empty list
means the record is valid.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "v1"

# Prose / scalar string fields that must be present and non-empty-typed.
REQUIRED_STRING_FIELDS = (
    "slug",
    "title",
    "repo_url",
    "one_liner",
    "what_it_is",
    "how_its_built",
    "how_to_apply",
    "diagram_architecture",
    "diagram_sequence",
    "generated_at",
    "source_commit",
    "model",
)

# List-of-string metadata fields (may be empty lists, but must be lists).
REQUIRED_LIST_FIELDS = (
    "capabilities",
    "components",
    "tech",
    "depends_on",
    "integrates_with",
    "patterns",
    "reuse_tags",
)

ENUMS = {
    "visibility": ("public", "private"),
    "status": ("idea", "building", "shipped"),
}


def validate_record(record: Any) -> list[str]:
    """Return a list of validation errors for *record* (empty list = valid)."""
    errors: list[str] = []

    if not isinstance(record, dict):
        return [f"record must be a dict, got {type(record).__name__}"]

    for field in REQUIRED_STRING_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")
        elif not isinstance(record[field], str):
            errors.append(f"field {field} must be a string")

    for field in REQUIRED_LIST_FIELDS:
        if field not in record:
            errors.append(f"missing required field: {field}")
        elif not isinstance(record[field], list):
            errors.append(f"field {field} must be a list")
        elif not all(isinstance(x, str) for x in record[field]):
            errors.append(f"field {field} must contain only strings")

    for field, allowed in ENUMS.items():
        if field not in record:
            errors.append(f"missing required field: {field}")
        elif record[field] not in allowed:
            errors.append(
                f"field {field} must be one of {allowed}, got {record.get(field)!r}"
            )

    if "thin" not in record:
        errors.append("missing required field: thin")
    elif not isinstance(record["thin"], bool):
        errors.append("field thin must be a boolean")

    if "todos" not in record:
        errors.append("missing required field: todos")
    elif not isinstance(record["todos"], list):
        errors.append("field todos must be a list")

    return errors
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_docsgen_schema.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add src/ghps/docsgen/__init__.py src/ghps/docsgen/schema.py tests/test_docsgen_schema.py
git commit -m "feat: add L0 record schema + validator

Session: <SESSION_ID>"
```

---

## Task 2: Hygiene — derive TODOs from branch/PR state

**Files:**
- Create: `src/ghps/docsgen/hygiene.py`
- Test: `tests/test_docsgen_hygiene.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_docsgen_hygiene.py`:

```python
"""Unit tests for repo-hygiene TODO derivation (pure, no network)."""

from __future__ import annotations

from ghps.docsgen import hygiene


def test_clean_repo_has_no_todos():
    todos = hygiene.derive_todos(branch_status=[], open_prs=[])
    assert todos == []


def test_branch_ahead_becomes_todo():
    todos = hygiene.derive_todos(
        branch_status=[{"name": "feat/x", "ahead_by": 3}],
        open_prs=[],
    )
    assert len(todos) == 1
    assert todos[0]["kind"] == "unmerged_branch"
    assert "feat/x" in todos[0]["detail"]
    assert "3" in todos[0]["detail"]


def test_branch_not_ahead_is_ignored():
    todos = hygiene.derive_todos(
        branch_status=[{"name": "stale", "ahead_by": 0}],
        open_prs=[],
    )
    assert todos == []


def test_open_pr_becomes_todo():
    todos = hygiene.derive_todos(
        branch_status=[],
        open_prs=[{"number": 7, "title": "Add feature"}],
    )
    assert len(todos) == 1
    assert todos[0]["kind"] == "open_pr"
    assert "#7" in todos[0]["detail"]
    assert "Add feature" in todos[0]["detail"]


def test_singular_vs_plural_commit_wording():
    one = hygiene.derive_todos([{"name": "b", "ahead_by": 1}], [])
    assert "1 commit ahead" in one[0]["detail"]
    many = hygiene.derive_todos([{"name": "b", "ahead_by": 2}], [])
    assert "2 commits ahead" in many[0]["detail"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_docsgen_hygiene.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.docsgen.hygiene'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ghps/docsgen/hygiene.py`:

```python
"""Derive the repo-hygiene TODO list from GitHub branch/PR state.

Pure function over already-fetched data — no network here. The GitHub API sees
branches and open PRs but NOT local uncommitted state, so local dirtiness is
deliberately out of scope for v1.
"""

from __future__ import annotations


def derive_todos(branch_status: list[dict], open_prs: list[dict]) -> list[dict]:
    """Build the ``todos[]`` block from branch and PR state.

    Args:
        branch_status: list of ``{"name": str, "ahead_by": int}`` for every
            non-default branch (ahead_by = commits ahead of the default branch).
        open_prs: list of ``{"number": int, "title": str}``.

    Returns a list of ``{"kind": str, "detail": str}`` dicts.
    """
    todos: list[dict] = []

    for branch in branch_status:
        ahead = branch.get("ahead_by", 0)
        if ahead and ahead > 0:
            noun = "commit" if ahead == 1 else "commits"
            todos.append(
                {
                    "kind": "unmerged_branch",
                    "detail": f"{branch['name']} is {ahead} {noun} ahead of the default branch",
                }
            )

    for pr in open_prs:
        todos.append(
            {
                "kind": "open_pr",
                "detail": f"PR #{pr['number']}: {pr['title']}",
            }
        )

    return todos
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_docsgen_hygiene.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/docsgen/hygiene.py tests/test_docsgen_hygiene.py
git commit -m "feat: derive repo-hygiene TODOs from branch/PR state

Session: <SESSION_ID>"
```

---

## Task 3: GitHub client — branches, compare, open PRs

**Files:**
- Modify: `src/ghps/github_client.py` (append three functions after `fetch_top_files`)
- Test: `tests/test_github_client.py` (append three test classes)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_github_client.py`:

```python
# ---------------------------------------------------------------------------
# fetch_branches / compare_commits / fetch_open_prs  (L0 hygiene)
# ---------------------------------------------------------------------------

class TestFetchBranches:
    @patch.object(github_client, "_session")
    def test_lists_branches_with_sha(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([
            {"name": "main", "commit": {"sha": "aaa111"}},
            {"name": "feat/x", "commit": {"sha": "bbb222"}},
        ])

        result = github_client.fetch_branches("owner", "repo")
        assert result == [
            {"name": "main", "commit_sha": "aaa111"},
            {"name": "feat/x", "commit_sha": "bbb222"},
        ]

    @patch.object(github_client, "_session")
    def test_repo_not_found_returns_empty(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        resp = MagicMock()
        resp.status_code = 404
        session.get.return_value = resp

        assert github_client.fetch_branches("owner", "missing") == []


class TestCompareCommits:
    @patch.object(github_client, "_session")
    def test_returns_ahead_by(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response({"ahead_by": 4})

        assert github_client.compare_commits("owner", "repo", "main", "feat/x") == 4

    @patch.object(github_client, "_session")
    def test_missing_comparison_returns_zero(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        resp = MagicMock()
        resp.status_code = 404
        session.get.return_value = resp

        assert github_client.compare_commits("owner", "repo", "main", "x") == 0


class TestFetchOpenPRs:
    @patch.object(github_client, "_session")
    def test_returns_number_and_title(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([
            {"number": 7, "title": "Add feature", "draft": False},
            {"number": 9, "title": "Fix bug", "draft": False},
        ])

        result = github_client.fetch_open_prs("owner", "repo")
        assert result == [
            {"number": 7, "title": "Add feature"},
            {"number": 9, "title": "Fix bug"},
        ]

    @patch.object(github_client, "_session")
    def test_no_prs_returns_empty(self, mock_session_fn):
        session = MagicMock()
        mock_session_fn.return_value = session
        session.get.return_value = _mock_response([])

        assert github_client.fetch_open_prs("owner", "repo") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_github_client.py -k "Branches or CompareCommits or OpenPRs" -v`
Expected: FAIL — `AttributeError: module 'ghps.github_client' has no attribute 'fetch_branches'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/ghps/github_client.py` (after `fetch_top_files`, before any `if __name__`):

```python
def fetch_branches(owner: str, repo: str) -> list[dict[str, str]]:
    """List branches for *owner/repo*.

    Returns a list of ``{"name": str, "commit_sha": str}``. Empty list if the
    repo is missing. Handles pagination.
    """
    session = _session()
    branches: list[dict[str, str]] = []
    page = 1

    while True:
        resp = session.get(
            f"{API_BASE}/repos/{owner}/{repo}/branches",
            params={"per_page": PER_PAGE, "page": page},
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()

        for b in data:
            branches.append(
                {"name": b["name"], "commit_sha": b.get("commit", {}).get("sha", "")}
            )

        if len(data) < PER_PAGE:
            break
        page += 1

    return branches


def compare_commits(owner: str, repo: str, base: str, head: str) -> int:
    """Return how many commits *head* is ahead of *base* (0 if unknown)."""
    session = _session()
    resp = session.get(f"{API_BASE}/repos/{owner}/{repo}/compare/{base}...{head}")
    if resp.status_code != 200:
        return 0
    return int(resp.json().get("ahead_by", 0))


def fetch_open_prs(owner: str, repo: str) -> list[dict[str, Any]]:
    """List open pull requests for *owner/repo*.

    Returns a list of ``{"number": int, "title": str}``. Empty list if none or
    if the repo is missing.
    """
    session = _session()
    resp = session.get(
        f"{API_BASE}/repos/{owner}/{repo}/pulls",
        params={"state": "open", "per_page": PER_PAGE},
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return [{"number": pr["number"], "title": pr.get("title", "")} for pr in resp.json()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_github_client.py -v`
Expected: PASS (all existing + 6 new)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/github_client.py tests/test_github_client.py
git commit -m "feat: add GitHub branch/compare/PR fetchers for hygiene

Session: <SESSION_ID>"
```

---

## Task 4: Repo context assembly

**Files:**
- Create: `src/ghps/docsgen/context.py`
- Test: `tests/test_docsgen_context.py`

This task assembles everything one repo's generation needs into a `RepoContext`, and decides the `thin` flag and `branch_status` (calling `compare_commits` only for non-default branches to bound API cost).

- [ ] **Step 1: Write the failing test**

Create `tests/test_docsgen_context.py`:

```python
"""Unit tests for per-repo context assembly (GitHub layer mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ghps.docsgen import context


def _repo_meta(**overrides):
    base = {
        "name": "demo",
        "description": "A demo repo",
        "language": "Python",
        "topics": ["demo"],
        "stars": 1,
        "updated_at": "2025-01-01T00:00:00Z",
        "html_url": "https://github.com/davidbmar/demo",
        "private": False,
    }
    base.update(overrides)
    return base


def _fake_gh(*, readme="# Demo", files=None, branches=None, prs=None, ahead=0):
    gh = MagicMock()
    gh.fetch_readme.return_value = readme
    gh.fetch_top_files.return_value = files or [("main.py", "print('hi')")]
    gh.fetch_branches.return_value = branches or [
        {"name": "main", "commit_sha": "aaa111"}
    ]
    gh.fetch_open_prs.return_value = prs or []
    gh.compare_commits.return_value = ahead
    return gh


def test_builds_context_with_slug_and_owner():
    gh = _fake_gh()
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    assert ctx.slug == "demo"
    assert ctx.owner == "davidbmar"
    assert ctx.head_sha == "aaa111"
    assert ctx.visibility == "public"


def test_default_branch_excluded_from_branch_status():
    gh = _fake_gh(
        branches=[
            {"name": "main", "commit_sha": "aaa"},
            {"name": "feat/x", "commit_sha": "bbb"},
        ],
        ahead=2,
    )
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    names = [b["name"] for b in ctx.branch_status]
    assert "main" not in names
    assert names == ["feat/x"]
    assert ctx.branch_status[0]["ahead_by"] == 2
    # compare_commits called once (only the non-default branch)
    assert gh.compare_commits.call_count == 1


def test_thin_when_readme_empty_and_no_source():
    gh = _fake_gh(readme="", files=[])
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    assert ctx.thin is True


def test_not_thin_with_real_readme():
    gh = _fake_gh(readme="# Demo\n\nA real project with content.")
    ctx = context.build_context(_repo_meta(), owner="davidbmar", gh=gh)
    assert ctx.thin is False


def test_private_visibility_propagates():
    gh = _fake_gh()
    ctx = context.build_context(_repo_meta(private=True), owner="davidbmar", gh=gh)
    assert ctx.visibility == "private"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_docsgen_context.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.docsgen.context'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ghps/docsgen/context.py`:

```python
"""Assemble everything a single repo's doc generation needs.

Pulls README, key source, branch/PR state from the GitHub layer (injectable for
tests), decides the ``thin`` flag, and computes ``branch_status`` by comparing
only NON-default branches against the default branch (bounds API cost).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ghps import github_client as _default_gh

# Treat a repo as "thin" when there is essentially nothing to document.
_THIN_README_CHARS = 80


@dataclass
class RepoContext:
    slug: str
    owner: str
    repo_url: str
    visibility: str  # "public" | "private"
    default_branch: str
    head_sha: str
    description: str
    language: str
    topics: list[str]
    readme: str
    source_files: list[tuple[str, str]]
    branch_status: list[dict] = field(default_factory=list)  # non-default branches
    open_prs: list[dict] = field(default_factory=list)
    thin: bool = False


def build_context(repo_meta: dict, *, owner: str, gh=_default_gh) -> RepoContext:
    """Build a :class:`RepoContext` for one repo.

    Args:
        repo_meta: a dict from ``github_client.fetch_repos`` (name, description,
            language, topics, html_url, private, ...).
        owner: the GitHub owner/org (e.g. "davidbmar").
        gh: the github_client module (injectable for tests).
    """
    name = repo_meta["name"]
    readme = gh.fetch_readme(owner, name)
    source_files = gh.fetch_top_files(owner, name)
    branches = gh.fetch_branches(owner, name)
    open_prs = gh.fetch_open_prs(owner, name)

    # The default branch is the one whose name is "main" or "master"; fall back
    # to the first branch. (We avoid a separate repo call: branches + heuristic.)
    branch_names = [b["name"] for b in branches]
    default_branch = "main"
    if "main" not in branch_names:
        default_branch = "master" if "master" in branch_names else (
            branch_names[0] if branch_names else "main"
        )

    head_sha = ""
    for b in branches:
        if b["name"] == default_branch:
            head_sha = b["commit_sha"]
            break

    branch_status: list[dict] = []
    for b in branches:
        if b["name"] == default_branch:
            continue
        ahead = gh.compare_commits(owner, name, default_branch, b["name"])
        branch_status.append({"name": b["name"], "ahead_by": ahead})

    thin = (
        len((readme or "").strip()) < _THIN_README_CHARS and not source_files
    )

    return RepoContext(
        slug=name,
        owner=owner,
        repo_url=repo_meta.get("html_url", f"https://github.com/{owner}/{name}"),
        visibility="private" if repo_meta.get("private") else "public",
        default_branch=default_branch,
        head_sha=head_sha,
        description=repo_meta.get("description", ""),
        language=repo_meta.get("language", ""),
        topics=list(repo_meta.get("topics", [])),
        readme=readme or "",
        source_files=source_files,
        branch_status=branch_status,
        open_prs=open_prs,
        thin=thin,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_docsgen_context.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/docsgen/context.py tests/test_docsgen_context.py
git commit -m "feat: assemble per-repo generation context

Session: <SESSION_ID>"
```

---

## Task 5: LLM client seam (DashScope + Anthropic)

**Files:**
- Create: `src/ghps/docsgen/llm_client.py`
- Test: `tests/test_docsgen_llm_client.py`

Both adapters use `requests` (no SDKs). `complete_json(system, user) -> dict` is the seam. The factory `get_client()` reads env so the model is a per-run cost/quality dial.

- [ ] **Step 1: Write the failing test**

Create `tests/test_docsgen_llm_client.py`:

```python
"""Unit tests for the provider-agnostic LLM client seam (HTTP mocked)."""

from __future__ import annotations

import json

import pytest
from unittest.mock import MagicMock

from ghps.docsgen import llm_client


def _resp(json_data, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    if status_code >= 400:
        r.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return r


class TestDashScopeClient:
    def test_parses_json_object_from_choices(self):
        session = MagicMock()
        payload = {"slug": "demo", "title": "Demo"}
        session.post.return_value = _resp(
            {"choices": [{"message": {"content": json.dumps(payload)}}]}
        )
        client = llm_client.DashScopeClient(
            api_key="k", base_url="https://x/v1", model="qwen-plus", session=session
        )
        result = client.complete_json("sys", "user")
        assert result == payload

    def test_sends_json_response_format(self):
        session = MagicMock()
        session.post.return_value = _resp(
            {"choices": [{"message": {"content": "{}"}}]}
        )
        client = llm_client.DashScopeClient(
            api_key="k", base_url="https://x/v1", model="qwen-plus", session=session
        )
        client.complete_json("sys", "user")
        _, kwargs = session.post.call_args
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        assert kwargs["headers"]["Authorization"] == "Bearer k"


class TestAnthropicClient:
    def test_strips_code_fence_and_parses(self):
        session = MagicMock()
        fenced = "```json\n{\"slug\": \"demo\"}\n```"
        session.post.return_value = _resp({"content": [{"text": fenced}]})
        client = llm_client.AnthropicClient(
            api_key="k", base_url="https://api.anthropic.com", model="claude-x",
            session=session,
        )
        assert client.complete_json("sys", "user") == {"slug": "demo"}


class TestGetClient:
    def test_dashscope_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "dashscope")
        monkeypatch.setenv("DASHSCOPE_API_KEY", "k")
        monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://x/v1")
        monkeypatch.setenv("DASHSCOPE_MODEL", "qwen-plus")
        client = llm_client.get_client()
        assert isinstance(client, llm_client.DashScopeClient)
        assert client.model == "qwen-plus"

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "dashscope")
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
            llm_client.get_client()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_docsgen_llm_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.docsgen.llm_client'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ghps/docsgen/llm_client.py`:

```python
"""Provider-agnostic LLM seam for doc generation.

`complete_json(system, user) -> dict` is the only method generators depend on.
Two adapters, both built on `requests` (no vendor SDKs):
  - DashScopeClient  — Alibaba Qwen via the OpenAI-compatible endpoint (v1).
  - AnthropicClient  — Claude via the Messages API (the cost/quality dial).

`get_client()` reads env so model choice is a per-run dial, not a commitment.
Keys never live in code; for this PUBLIC repo they come from a gitignored .env
locally and GitHub Actions secrets in CI.
"""

from __future__ import annotations

import json
import os
from typing import Protocol

import requests

_TIMEOUT = 120
_MAX_TOKENS = 4096


class LLMClient(Protocol):
    model: str

    def complete_json(self, system: str, user: str) -> dict:
        """Return a parsed JSON object from the model."""
        ...


def _extract_json(text: str) -> dict:
    """Parse a JSON object from model text, tolerating ```json fences."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s[: -3]
        if s.startswith("json"):
            s = s[4:]
    return json.loads(s.strip())


class DashScopeClient:
    """Alibaba Qwen via the DashScope OpenAI-compatible chat-completions API."""

    def __init__(self, api_key: str, base_url: str, model: str, session=None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._session = session or requests.Session()

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._session.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(content)


class AnthropicClient:
    """Claude via the Anthropic Messages API."""

    def __init__(self, api_key: str, base_url: str, model: str, session=None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._session = session or requests.Session()

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._session.post(
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": _MAX_TOKENS,
                "system": system + "\n\nRespond with a single JSON object only.",
                "messages": [{"role": "user", "content": user}],
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        return _extract_json(text)


def get_client(provider: str | None = None) -> LLMClient:
    """Construct an LLM client from env (provider defaults to $LLM_PROVIDER)."""
    provider = (provider or os.environ.get("LLM_PROVIDER", "dashscope")).lower()

    if provider == "dashscope":
        key = os.environ.get("DASHSCOPE_API_KEY")
        if not key:
            raise RuntimeError("DASHSCOPE_API_KEY is not set")
        return DashScopeClient(
            api_key=key,
            base_url=os.environ.get(
                "DASHSCOPE_BASE_URL",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            ),
            model=os.environ.get("DASHSCOPE_MODEL", "qwen-plus"),
        )

    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        return AnthropicClient(
            api_key=key,
            base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        )

    raise RuntimeError(f"unknown LLM provider: {provider}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_docsgen_llm_client.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/docsgen/llm_client.py tests/test_docsgen_llm_client.py
git commit -m "feat: provider-agnostic LLM client seam (DashScope + Anthropic)

Session: <SESSION_ID>"
```

---

## Task 6: Record generation (prompt + validate + retry + fill)

**Files:**
- Create: `src/ghps/docsgen/record_gen.py`
- Test: `tests/test_docsgen_record_gen.py`

`generate_record` asks the LLM for the prose + diagram + typed-metadata fields, then *the generator itself* fills the deterministic fields (`slug`, `repo_url`, `visibility`, `thin`, `todos`, provenance) — never trusting the LLM for those. Invalid output triggers one retry, then a `RecordGenerationError`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_docsgen_record_gen.py`:

```python
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
        return self._returns.pop(0)


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


def test_thin_repo_still_produces_valid_record():
    client = _FakeClient(dict(_LLM_FIELDS))
    rec = record_gen.generate_record(_ctx(thin=True, readme="", source_files=[]), client)
    assert rec["thin"] is True
    assert record_gen.schema.validate_record(rec) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_docsgen_record_gen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.docsgen.record_gen'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ghps/docsgen/record_gen.py`:

```python
"""Turn a RepoContext into a validated structured record via the LLM.

The LLM owns the prose, diagrams, and typed-metadata fields. The generator owns
the deterministic fields — slug, repo_url, visibility, thin, todos, provenance —
and never trusts the model for them. Invalid LLM output triggers one retry, then
a RecordGenerationError (caller marks a failure; never renders a broken page).
"""

from __future__ import annotations

from datetime import datetime, timezone

from ghps.docsgen import hygiene, schema
from ghps.docsgen.context import RepoContext

_MAX_README_CHARS = 6000
_MAX_FILE_CHARS = 1500
_MAX_FILES = 6

# Fields the model is asked to author.
_LLM_OWNED = (
    "title",
    "one_liner",
    "what_it_is",
    "how_its_built",
    "how_to_apply",
    "diagram_architecture",
    "diagram_sequence",
    "capabilities",
    "components",
    "tech",
    "depends_on",
    "integrates_with",
    "patterns",
    "reuse_tags",
)

_SYSTEM = """You are a senior engineer writing a precise, reusable project brief.
Output ONE JSON object with EXACTLY these keys and no others:
  title (string), one_liner (string),
  what_it_is (string), how_its_built (string), how_to_apply (string),
  diagram_architecture (Mermaid flowchart source string),
  diagram_sequence (Mermaid sequenceDiagram source string),
  capabilities, components, tech, depends_on, integrates_with, patterns,
  reuse_tags (all arrays of short strings).
The sequenceDiagram MUST reflect how the code actually runs (who calls whom) —
do not hand-wave it from the README. Keep prose concrete and free of marketing.
Mermaid must be valid: start diagram_architecture with 'flowchart' and
diagram_sequence with 'sequenceDiagram'."""


class RecordGenerationError(RuntimeError):
    """Raised when the LLM cannot produce a schema-valid record after retry."""


def build_messages(ctx: RepoContext) -> tuple[str, str]:
    """Return (system, user) prompt strings for *ctx*."""
    files_block = "\n\n".join(
        f"--- {path} ---\n{content[:_MAX_FILE_CHARS]}"
        for path, content in ctx.source_files[:_MAX_FILES]
    )
    thin_note = (
        "\nNOTE: this repo is THIN (fork/stub/empty). Keep every field short and "
        "factual; do not invent capabilities.\n"
        if ctx.thin
        else ""
    )
    user = f"""Repository: {ctx.slug}
URL: {ctx.repo_url}
Primary language: {ctx.language}
Topics: {", ".join(ctx.topics) or "(none)"}
Description: {ctx.description or "(none)"}{thin_note}

README (truncated):
{ctx.readme[:_MAX_README_CHARS] or "(no README)"}

Key source files (truncated):
{files_block or "(no source files retrieved)"}
"""
    return _SYSTEM, user


def generate_record(ctx: RepoContext, client, *, model: str | None = None) -> dict:
    """Generate a validated record for *ctx* using *client*.

    *model* is recorded as provenance; defaults to ``client.model``.
    """
    system, user = build_messages(ctx)

    last_errors: list[str] = []
    for _attempt in range(2):
        llm_part = client.complete_json(system, user)
        record = _assemble(ctx, llm_part, model or getattr(client, "model", "unknown"))
        last_errors = schema.validate_record(record)
        if not last_errors:
            return record

    raise RecordGenerationError(
        f"{ctx.slug}: record invalid after retry: {last_errors}"
    )


def _assemble(ctx: RepoContext, llm_part: dict, model: str) -> dict:
    """Merge LLM-owned fields with deterministic generator-owned fields."""
    record: dict = {field: llm_part.get(field) for field in _LLM_OWNED}
    record.update(
        {
            "slug": ctx.slug,
            "repo_url": ctx.repo_url,
            "visibility": ctx.visibility,
            "status": "shipped",
            "thin": ctx.thin,
            "todos": hygiene.derive_todos(ctx.branch_status, ctx.open_prs),
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "source_commit": ctx.head_sha[:7] if ctx.head_sha else "",
            "model": model,
        }
    )
    return record
```

Note: `generated_at` uses `datetime.now(timezone.utc)` — fine in normal Python (the workflow-script restriction on `Date.now` does not apply here).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_docsgen_record_gen.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/docsgen/record_gen.py tests/test_docsgen_record_gen.py
git commit -m "feat: generate validated structured records via LLM seam

Session: <SESSION_ID>"
```

---

## Task 7: Renderer (record → HTML page)

**Files:**
- Create: `src/ghps/docsgen/render.py`
- Test: `tests/test_docsgen_render.py`

Pure-Python rendering: prose `html.escape`d, Mermaid source placed in `<pre class="mermaid">` (NOT escaped — Mermaid needs raw text; it is generator-owned diagram source, and the page is static), JSON island via `json.dumps`, JSON-LD `SoftwareSourceCode` block, hygiene panel.

- [ ] **Step 1: Write the failing test**

Create `tests/test_docsgen_render.py`:

```python
"""Golden-structure tests for the HTML renderer (no network)."""

from __future__ import annotations

import json
import re

from ghps.docsgen import render


def _record(**overrides) -> dict:
    base = {
        "slug": "demo",
        "title": "Demo Project",
        "repo_url": "https://github.com/davidbmar/demo",
        "visibility": "public",
        "status": "shipped",
        "thin": False,
        "one_liner": "Does a thing.",
        "what_it_is": "A demonstration with <script>danger</script>.",
        "how_its_built": "With Python.",
        "how_to_apply": "Copy it.",
        "diagram_architecture": "flowchart LR; A-->B",
        "diagram_sequence": "sequenceDiagram; A->>B: hi",
        "capabilities": ["demoing"],
        "components": ["main"],
        "tech": ["python"],
        "depends_on": [],
        "integrates_with": [],
        "patterns": ["adapter"],
        "reuse_tags": ["demo"],
        "todos": [{"kind": "unmerged_branch", "detail": "feat/x is 2 commits ahead"}],
        "generated_at": "2026-06-13T00:00:00Z",
        "source_commit": "abc1234",
        "model": "qwen-plus",
    }
    base.update(overrides)
    return base


def test_has_json_data_island_matching_record():
    html = render.render_page(_record())
    m = re.search(
        r'<script type="application/json" id="project-data">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert m is not None
    assert json.loads(m.group(1))["slug"] == "demo"


def test_includes_both_mermaid_blocks():
    html = render.render_page(_record())
    assert html.count('class="mermaid"') == 2
    assert "flowchart LR; A--&gt;B" not in html  # mermaid source must NOT be escaped
    assert "flowchart LR; A-->B" in html
    assert "sequenceDiagram; A->>B: hi" in html


def test_includes_json_ld_software_source_code():
    html = render.render_page(_record())
    assert '"@type": "SoftwareSourceCode"' in html


def test_escapes_prose_to_prevent_injection():
    html = render.render_page(_record())
    assert "<script>danger</script>" not in html
    assert "&lt;script&gt;danger&lt;/script&gt;" in html


def test_renders_hygiene_panel_when_todos_present():
    html = render.render_page(_record())
    assert "Needs attention" in html
    assert "feat/x is 2 commits ahead" in html


def test_renders_all_clear_when_no_todos():
    html = render.render_page(_record(todos=[]))
    assert "all on main" in html.lower()


def test_thin_badge_when_thin():
    html = render.render_page(_record(thin=True))
    assert "thin" in html.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_docsgen_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.docsgen.render'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ghps/docsgen/render.py`:

```python
"""Render a structured record into a self-contained HTML page.

Pure Python (no Jinja). Prose is HTML-escaped; Mermaid diagram source is placed
raw inside <pre class="mermaid"> (Mermaid requires unescaped text, and the source
is generator-owned, not user input). Each page embeds a JSON data island and a
JSON-LD SoftwareSourceCode block so machine-readability falls out for free.
"""

from __future__ import annotations

import html
import json

_MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"


def _tags(items: list[str]) -> str:
    if not items:
        return '<span class="muted">—</span>'
    return "".join(f'<span class="tag">{html.escape(t)}</span>' for t in items)


def _meta_row(label: str, items: list[str]) -> str:
    return (
        f'<div class="meta-row"><span class="meta-label">{html.escape(label)}</span>'
        f'<span class="meta-tags">{_tags(items)}</span></div>'
    )


def _hygiene_panel(record: dict) -> str:
    todos = record.get("todos", [])
    if not todos:
        return '<section class="hygiene clean"><h2>Repo hygiene</h2><p>✓ all on main — nothing unmerged.</p></section>'
    items = "".join(
        f'<li><strong>{html.escape(t.get("kind", ""))}</strong>: '
        f'{html.escape(t.get("detail", ""))}</li>'
        for t in todos
    )
    return (
        '<section class="hygiene needs-attention"><h2>⚠ Needs attention</h2>'
        f"<ul>{items}</ul></section>"
    )


def _json_ld(record: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": record.get("title", record.get("slug", "")),
        "description": record.get("one_liner", ""),
        "codeRepository": record.get("repo_url", ""),
        "programmingLanguage": record.get("tech", []),
    }
    return json.dumps(data, indent=2)


def render_page(record: dict) -> str:
    """Return a complete HTML document for *record*."""
    title = html.escape(record.get("title", record.get("slug", "")))
    thin_badge = (
        '<span class="badge thin">thin</span>' if record.get("thin") else ""
    )
    visibility = html.escape(record.get("visibility", ""))
    status = html.escape(record.get("status", ""))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · davidbmar.com</title>
<script type="application/json" id="project-data">{json.dumps(record)}</script>
<script type="application/ld+json">{_json_ld(record)}</script>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 920px; margin: 2rem auto;
          padding: 0 1.25rem; }}
  h1 {{ margin-bottom: .25rem; }}
  .one-liner {{ font-size: 1.15rem; opacity: .85; }}
  .badge {{ font-size: .72rem; padding: .15rem .5rem; border-radius: 999px;
            background: #ddd; color: #222; margin-left: .5rem; }}
  .badge.thin {{ background: #b88600; color: #fff; }}
  .tag {{ display: inline-block; background: #eef; color: #224; border-radius: 6px;
          padding: .1rem .45rem; margin: .1rem; font-size: .82rem; }}
  .muted {{ opacity: .5; }}
  .meta-row {{ display: flex; gap: .75rem; margin: .35rem 0; }}
  .meta-label {{ flex: 0 0 9rem; font-weight: 600; opacity: .7; }}
  .hygiene {{ border-left: 4px solid #2a7; padding: .5rem 1rem; margin: 1.5rem 0;
              background: #f4fbf7; }}
  .hygiene.needs-attention {{ border-color: #d33; background: #fdf4f4; }}
  pre.mermaid {{ background: #fafafa; padding: 1rem; border-radius: 8px; }}
  a {{ color: #2563eb; }}
</style>
</head>
<body>
<header>
  <h1>{title}{thin_badge}</h1>
  <p class="one-liner">{html.escape(record.get("one_liner", ""))}</p>
  <p><a href="{html.escape(record.get("repo_url", ""))}">{html.escape(record.get("repo_url", ""))}</a>
     &nbsp;·&nbsp; {visibility} &nbsp;·&nbsp; {status}</p>
</header>

<section><h2>What it is</h2><p>{html.escape(record.get("what_it_is", ""))}</p></section>

<section><h2>Architecture</h2>
  <pre class="mermaid">{record.get("diagram_architecture", "")}</pre>
</section>

<section><h2>How it's built</h2><p>{html.escape(record.get("how_its_built", ""))}</p></section>

<section><h2>How it runs</h2>
  <pre class="mermaid">{record.get("diagram_sequence", "")}</pre>
</section>

<section><h2>How to apply &amp; reuse</h2><p>{html.escape(record.get("how_to_apply", ""))}</p></section>

<section><h2>At a glance</h2>
  {_meta_row("Capabilities", record.get("capabilities", []))}
  {_meta_row("Components", record.get("components", []))}
  {_meta_row("Tech", record.get("tech", []))}
  {_meta_row("Depends on", record.get("depends_on", []))}
  {_meta_row("Integrates with", record.get("integrates_with", []))}
  {_meta_row("Patterns", record.get("patterns", []))}
  {_meta_row("Reuse tags", record.get("reuse_tags", []))}
</section>

{_hygiene_panel(record)}

<footer class="muted">
  <p>Generated {html.escape(record.get("generated_at", ""))} ·
     commit {html.escape(record.get("source_commit", ""))} ·
     model {html.escape(record.get("model", ""))}</p>
</footer>

<script type="module">
  import mermaid from "{_MERMAID_CDN}";
  mermaid.initialize({{ startOnLoad: true }});
</script>
</body>
</html>
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_docsgen_render.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/docsgen/render.py tests/test_docsgen_render.py
git commit -m "feat: render structured record to HTML page (JSON island + Mermaid)

Session: <SESSION_ID>"
```

---

## Task 8: Aggregator (records → projects.json)

**Files:**
- Create: `src/ghps/docsgen/aggregate.py`
- Test: `tests/test_docsgen_aggregate.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_docsgen_aggregate.py`:

```python
"""Unit tests for aggregating per-repo records into the machine feed."""

from __future__ import annotations

import json

from ghps.docsgen import aggregate


def _write_record(dir_path, slug, **overrides):
    rec = {"slug": slug, "title": slug.title(), "thin": False}
    rec.update(overrides)
    (dir_path / f"{slug}.record.json").write_text(json.dumps(rec))
    return rec


def test_aggregates_all_records_sorted_by_slug(tmp_path):
    records_dir = tmp_path / "projects"
    records_dir.mkdir()
    _write_record(records_dir, "zebra")
    _write_record(records_dir, "alpha")
    out = tmp_path / "web" / "data" / "projects.json"

    result = aggregate.aggregate_records(str(records_dir), str(out))

    assert out.exists()
    data = json.loads(out.read_text())
    assert [p["slug"] for p in data["projects"]] == ["alpha", "zebra"]
    assert data["count"] == 2
    assert result["count"] == 2


def test_ignores_non_record_files(tmp_path):
    records_dir = tmp_path / "projects"
    records_dir.mkdir()
    _write_record(records_dir, "alpha")
    (records_dir / "README.md").write_text("not a record")
    out = tmp_path / "projects.json"

    aggregate.aggregate_records(str(records_dir), str(out))
    data = json.loads(out.read_text())
    assert data["count"] == 1


def test_skips_malformed_json(tmp_path):
    records_dir = tmp_path / "projects"
    records_dir.mkdir()
    _write_record(records_dir, "good")
    (records_dir / "broken.record.json").write_text("{not json")
    out = tmp_path / "projects.json"

    result = aggregate.aggregate_records(str(records_dir), str(out))
    assert result["count"] == 1
    assert "broken" in result["skipped"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_docsgen_aggregate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.docsgen.aggregate'`

- [ ] **Step 3: Write minimal implementation**

Create `src/ghps/docsgen/aggregate.py`:

```python
"""Roll all per-repo records into web/data/projects.json (the L2/L3 feed)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_SUFFIX = ".record.json"


def aggregate_records(records_dir: str, output_path: str) -> dict:
    """Aggregate every ``*.record.json`` in *records_dir* into *output_path*.

    Returns a summary dict ``{"count": int, "skipped": list[str]}``.
    """
    projects: list[dict] = []
    skipped: list[str] = []

    src = Path(records_dir)
    for path in sorted(src.glob(f"*{_SUFFIX}")):
        try:
            projects.append(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("skipping %s: %s", path.name, exc)
            skipped.append(path.name)

    projects.sort(key=lambda p: p.get("slug", ""))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(projects),
        "projects": projects,
    }
    out.write_text(json.dumps(payload, indent=2))
    logger.info("aggregated %d records to %s", len(projects), output_path)

    return {"count": len(projects), "skipped": skipped}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_docsgen_aggregate.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/docsgen/aggregate.py tests/test_docsgen_aggregate.py
git commit -m "feat: aggregate records into web/data/projects.json feed

Session: <SESSION_ID>"
```

---

## Task 9: Orchestrator + CLI command + Makefile

**Files:**
- Create: `src/ghps/docsgen/generate.py`
- Modify: `src/ghps/cli.py` (add `gen-docs` command)
- Modify: `Makefile` (add `gen-docs` target)
- Create: `.env.example`
- Modify: `.gitignore` (ensure `.env` is ignored — verify first)
- Test: extend `tests/test_docsgen_aggregate.py` is not enough — add `tests/test_docsgen_generate.py`

The orchestrator is idempotent (skips repos whose record exists unless `force`), supports `--only <slug>` and `--limit`, writes records to `projects/`, renders HTML to `web/projects/`, and aggregates to `web/data/projects.json`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_docsgen_generate.py`:

```python
"""Orchestrator tests — GitHub + LLM layers faked, filesystem via tmp_path."""

from __future__ import annotations

import json

from ghps.docsgen import generate


_LLM_FIELDS = {
    "title": "Demo", "one_liner": "x", "what_it_is": "x", "how_its_built": "x",
    "how_to_apply": "x", "diagram_architecture": "flowchart LR; A-->B",
    "diagram_sequence": "sequenceDiagram; A->>B: hi", "capabilities": [],
    "components": [], "tech": ["python"], "depends_on": [], "integrates_with": [],
    "patterns": [], "reuse_tags": [],
}


class _FakeClient:
    model = "fake"

    def complete_json(self, system, user):
        return dict(_LLM_FIELDS)


def _fake_gh():
    import types

    def fetch_repos(username):
        return [
            {"name": "alpha", "html_url": "https://github.com/davidbmar/alpha",
             "private": False, "description": "", "language": "Python",
             "topics": [], "stars": 0, "updated_at": ""},
        ]

    m = types.SimpleNamespace(
        fetch_repos=fetch_repos,
        fetch_readme=lambda o, r: "# Alpha\n\nReal content here for the project.",
        fetch_top_files=lambda o, r: [("main.py", "print('hi')")],
        fetch_branches=lambda o, r: [{"name": "main", "commit_sha": "abc1234"}],
        fetch_open_prs=lambda o, r: [],
        compare_commits=lambda o, r, b, h: 0,
    )
    return m


def test_generate_all_writes_record_html_and_aggregate(tmp_path):
    result = generate.generate_all(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        client=_FakeClient(),
        gh=_fake_gh(),
    )
    assert result["generated"] == 1
    assert (tmp_path / "projects" / "alpha.record.json").exists()
    assert (tmp_path / "web" / "projects" / "alpha.html").exists()
    feed = json.loads((tmp_path / "web" / "data" / "projects.json").read_text())
    assert feed["count"] == 1


def test_idempotent_skips_existing_unless_force(tmp_path):
    args = dict(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        gh=_fake_gh(),
    )
    generate.generate_all(client=_FakeClient(), **args)
    second = generate.generate_all(client=_FakeClient(), **args)
    assert second["generated"] == 0
    assert second["skipped"] == 1
    forced = generate.generate_all(client=_FakeClient(), force=True, **args)
    assert forced["generated"] == 1


def test_only_filters_to_one_slug(tmp_path):
    result = generate.generate_all(
        owner="davidbmar",
        records_dir=str(tmp_path / "projects"),
        html_dir=str(tmp_path / "web" / "projects"),
        feed_path=str(tmp_path / "web" / "data" / "projects.json"),
        client=_FakeClient(),
        gh=_fake_gh(),
        only="nonexistent",
    )
    assert result["generated"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_docsgen_generate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.docsgen.generate'`

- [ ] **Step 3: Write the orchestrator**

Create `src/ghps/docsgen/generate.py`:

```python
"""Orchestrate L0 doc generation across one or many repos.

Idempotent: skips repos whose record already exists unless force=True. Writes
the record (projects/<slug>.record.json), the HTML page (web/projects/<slug>.html),
and finally aggregates all records into the machine feed.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from ghps import github_client as _default_gh
from ghps.docsgen import aggregate, context, record_gen, render
from ghps.docsgen.record_gen import RecordGenerationError

logger = logging.getLogger(__name__)


def generate_one(
    repo_meta: dict,
    *,
    owner: str,
    records_dir: str,
    html_dir: str,
    client,
    gh=_default_gh,
    model: str | None = None,
) -> dict:
    """Generate record + HTML for a single repo. Returns the record dict."""
    ctx = context.build_context(repo_meta, owner=owner, gh=gh)
    record = record_gen.generate_record(ctx, client, model=model)

    Path(records_dir).mkdir(parents=True, exist_ok=True)
    Path(html_dir).mkdir(parents=True, exist_ok=True)

    record_path = Path(records_dir) / f"{record['slug']}.record.json"
    record_path.write_text(json.dumps(record, indent=2))

    html_path = Path(html_dir) / f"{record['slug']}.html"
    html_path.write_text(render.render_page(record))

    logger.info("generated %s", record["slug"])
    return record


def generate_all(
    *,
    owner: str,
    records_dir: str,
    html_dir: str,
    feed_path: str,
    client,
    gh=_default_gh,
    only: str | None = None,
    limit: int | None = None,
    force: bool = False,
    model: str | None = None,
) -> dict:
    """Generate docs for every repo owned by *owner*.

    Returns ``{"generated": int, "skipped": int, "failed": list[str]}``.
    """
    repos = gh.fetch_repos(owner)
    if only:
        repos = [r for r in repos if r["name"] == only]
    if limit is not None:
        repos = repos[:limit]

    generated = 0
    skipped = 0
    failed: list[str] = []

    for repo_meta in repos:
        slug = repo_meta["name"]
        record_path = Path(records_dir) / f"{slug}.record.json"
        if record_path.exists() and not force:
            skipped += 1
            logger.info("skipping %s (record exists)", slug)
            continue
        try:
            generate_one(
                repo_meta,
                owner=owner,
                records_dir=records_dir,
                html_dir=html_dir,
                client=client,
                gh=gh,
                model=model,
            )
            generated += 1
        except (RecordGenerationError, KeyError, OSError) as exc:
            logger.warning("FAILED %s: %s", slug, exc)
            failed.append(slug)

    aggregate.aggregate_records(records_dir, feed_path)
    return {"generated": generated, "skipped": skipped, "failed": failed}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_docsgen_generate.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Add the CLI command**

In `src/ghps/cli.py`, add this command after the `export` command (before `serve`):

```python
@main.command(name="gen-docs")
@click.option("--owner", default="davidbmar", help="GitHub owner/org to document.")
@click.option("--only", default=None, help="Generate just one repo by slug.")
@click.option("--limit", default=None, type=int, help="Cap number of repos (cost control).")
@click.option("--force", is_flag=True, help="Regenerate even if a record exists.")
@click.option("--provider", default=None, help="LLM provider (dashscope|anthropic).")
@click.option("--model", default=None, help="Override model id (provenance + dial).")
def gen_docs(owner, only, limit, force, provider, model):
    """Generate AI-written, machine-readable docs (L0) for each repo."""
    from ghps.docsgen import generate
    from ghps.docsgen.llm_client import get_client

    client = get_client(provider)
    if model:
        client.model = model

    result = generate.generate_all(
        owner=owner,
        records_dir="projects",
        html_dir="web/projects",
        feed_path="web/data/projects.json",
        client=client,
        only=only,
        limit=limit,
        force=force,
        model=model,
    )

    click.echo(click.style("Doc generation complete!", fg="green", bold=True))
    click.echo(f"  generated: {result['generated']}")
    click.echo(f"  skipped:   {result['skipped']}")
    if result["failed"]:
        click.echo(click.style(f"  failed:    {result['failed']}", fg="red"))
```

- [ ] **Step 6: Add the Makefile target**

In `Makefile`, add after the `export` target:

```makefile
gen-docs:
	ghps gen-docs $(if $(ONLY),--only $(ONLY),) $(if $(LIMIT),--limit $(LIMIT),)
```

And add `gen-docs` to the `.PHONY` line if one exists.

- [ ] **Step 7: Create `.env.example` and verify `.gitignore`**

Create `.env.example`:

```bash
# GitHub (read-only public_repo scope is enough; private repos need full repo)
GITHUB_TOKEN=ghp_xxx

# L0 doc generator — LLM provider (reuse the existing Alibaba Qwen key for v1)
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen-plus

# Optional cost/quality dial — escalate flagship repos to Claude
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-xxx
# ANTHROPIC_MODEL=claude-sonnet-4-6
```

Verify `.env` is gitignored:

Run: `grep -qx '.env' .gitignore && echo "ok: .env ignored" || echo "MISSING"`
If it prints `MISSING`, append `.env` to `.gitignore`.

- [ ] **Step 8: Run the full suite + lint**

Run: `python3 -m pytest tests/ -v && python3 -m py_compile src/ghps/*.py src/ghps/docsgen/*.py`
Expected: all green; no compile errors.

- [ ] **Step 9: Commit**

```bash
git add src/ghps/docsgen/generate.py tests/test_docsgen_generate.py \
        src/ghps/cli.py Makefile .env.example .gitignore
git commit -m "feat: gen-docs orchestrator + CLI command + env scaffolding

Session: <SESSION_ID>"
```

---

## Task 10: Guinea-pig run — `generate_title_headline_hooks` end-to-end + deploy

This is the spec's success gate: the first real generation target is `generate_title_headline_hooks`; its page must read true and show **"✓ all on main"** before any batch run. This task uses the live LLM + GitHub APIs, so it requires real keys in `.env`.

- [ ] **Step 1: Session-start sanity check (per global CLAUDE.md)**

Run:
```bash
which python && readlink -f .venv 2>/dev/null | head
.venv/bin/python -c "import requests, click; print('ok')"
test -f .env && grep -q DASHSCOPE_API_KEY .env && echo "dashscope key present" || echo "MISSING DASHSCOPE KEY"
```
Expected: `ok` and `dashscope key present`. If the key is missing, stop and add it to `.env` (reuse the existing `alibaba-headline-gen` key) before continuing.

- [ ] **Step 2: Generate just the guinea pig**

Run:
```bash
ghps gen-docs --only generate_title_headline_hooks --force
```
Expected output: `generated: 1`, `skipped: 0`, no failures.

- [ ] **Step 3: Verify the record is schema-valid and provenance is real**

Run:
```bash
python3 -c "
import json
from ghps.docsgen import schema
rec = json.load(open('projects/generate_title_headline_hooks.record.json'))
errs = schema.validate_record(rec)
print('errors:', errs)
print('thin:', rec['thin'], '| commit:', rec['source_commit'], '| model:', rec['model'])
print('todos:', rec['todos'])
"
```
Expected: `errors: []`, `thin: False`, a real 7-char commit, the model id, and `todos: []` (since the repo's work is all on main — this confirms the hygiene panel will show "✓ all on main").

- [ ] **Step 4: Visually verify the rendered page (browse)**

Use the `/browse` skill (gstack) to open the generated page locally and confirm both diagrams render and the hygiene panel is correct:

```bash
python3 -m http.server 8099 --directory web &
SERVER_PID=$!
sleep 1
```

Then drive the browser to `http://localhost:8099/projects/generate_title_headline_hooks.html` and check:
- Both Mermaid diagrams render (architecture flowchart + sequence diagram), not raw text.
- The "Repo hygiene" panel shows **"✓ all on main"**.
- Prose sections (What it is / How it's built / How to apply) read true to the actual project.
- The JSON island `#project-data` is present (View Source).

Then stop the server (per global server-management rule — verify it's dead):
```bash
kill $SERVER_PID 2>/dev/null
sleep 1
lsof -ti :8099 | xargs kill -9 2>/dev/null
lsof -ti :8099 && echo "STILL RUNNING" || echo "port clear"
```

If anything reads false or a diagram is broken, re-run `gen-docs --only ... --force` (LLM variance) or escalate the model: `--provider anthropic --model claude-sonnet-4-6`. Do not proceed to deploy until the page is correct.

- [ ] **Step 5: Commit the guinea-pig record + page + feed**

```bash
git add projects/generate_title_headline_hooks.record.json \
        web/projects/generate_title_headline_hooks.html \
        web/data/projects.json
git commit -m "feat: L0 guinea-pig — generate_title_headline_hooks doc page

Session: <SESSION_ID>"
```

- [ ] **Step 6: Deploy and verify live**

Run:
```bash
make deploy
```
This runs `ghps export` + validation, then `aws s3 sync web/ s3://davidbmar-com/ --delete` and a CloudFront invalidation (`E3RCY6XA80ANRT`).

⚠ **Outward-facing action** — this publishes to the live davidbmar.com. The work above (page reads true, diagrams render, hygiene correct) is the authorization gate. Confirm Step 4 passed before running.

Then verify the live URL with the `/browse` skill:
`https://davidbmar.com/projects/generate_title_headline_hooks.html`
Confirm the same checks as Step 4 on the deployed page (allow a minute for CloudFront invalidation).

- [ ] **Step 7: Report**

Report to the user: the live URL, whether both diagrams render, the hygiene panel state, and the per-page generation cost/token estimate so the 137-repo batch can be budgeted. Do **not** auto-run the full batch — that is a separate, user-authorized step (137 LLM calls).

---

## Task 11 (optional, stretch): GitHub Actions workflow

Only do this if the user wants scheduled/CI generation. The CLI already satisfies the spec's orchestration requirement; this just automates it with the DashScope key as an Actions secret.

**Files:**
- Create: `.github/workflows/gen-docs.yml`

- [ ] **Step 1: Create the workflow**

```yaml
name: Generate project docs (L0)

on:
  workflow_dispatch:
    inputs:
      only:
        description: "Single repo slug (blank = all)"
        required: false
      limit:
        description: "Cap repo count (blank = no cap)"
        required: false

jobs:
  gen-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - name: Generate docs
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          LLM_PROVIDER: dashscope
          DASHSCOPE_API_KEY: ${{ secrets.DASHSCOPE_API_KEY }}
          DASHSCOPE_BASE_URL: ${{ secrets.DASHSCOPE_BASE_URL }}
          DASHSCOPE_MODEL: ${{ secrets.DASHSCOPE_MODEL }}
        run: |
          ghps gen-docs \
            ${{ inputs.only && format('--only {0}', inputs.only) || '' }} \
            ${{ inputs.limit && format('--limit {0}', inputs.limit) || '' }}
      - name: Commit generated docs
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add projects/ web/projects/ web/data/projects.json
          git commit -m "chore: regenerate L0 project docs [skip ci]" || echo "no changes"
          git push
```

Note: deployment stays manual (`make deploy`) — the Action only regenerates records/pages. Document the three `DASHSCOPE_*` secrets in the repo settings.

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/gen-docs.yml
git commit -m "ci: workflow_dispatch for L0 doc generation

Session: <SESSION_ID>"
```

---

## Self-review (run against the spec)

**Spec coverage:**
- Rich HTML page per repo with Mermaid → Task 7 (render) + Task 10 (live verify). ✅
- Structured record source of truth → Task 1 (schema) + Task 6 (generate). ✅
- Machine-readability: JSON island + JSON-LD per page → Task 7; aggregated `web/data/projects.json` → Task 8. ✅
- Centrally stored records (`projects/<slug>.record.json`) → Task 9 orchestrator. ✅
- All repos incl. forks/stubs with `thin` flag → Task 4 (context decides thin) + Task 6 (propagates) + Task 7 (badge). ✅
- Provider-agnostic LLM seam, reuse Qwen key → Task 5 (`get_client`) + Task 9 env scaffolding. ✅
- Architecture flowchart + sequenceDiagram per project → Task 6 prompt requires both; Task 7 renders both. ✅
- Repo-hygiene TODO panel (branches/PRs), "✓ all on main" when clean → Task 2 (derive) + Task 3 (GitHub calls) + Task 7 (panel). ✅
- Publish via existing `deploy.sh` (S3 + CloudFront) → Task 10 Step 6. ✅
- Components table (repo_fetch, llm_client, record_gen, hygiene, render, aggregate, cli/Action) → Tasks 3–9, all independently tested. ✅
- Testing: schema validation, deterministic pure-function tests, golden render, guinea-pig end-to-end → Tasks 1,2,7 + Task 10. ✅
- Success criteria 1–5 → Tasks 9 (every repo), 7+10 (both diagrams), 7+8 (machine feed), 2+7+10 (hygiene), 10 (guinea pig deployed). ✅
- Out-of-scope (commit-back, L2 wiring, L3 graph, local dirtiness) → not implemented; record schema leaves seams (`reuse_tags`, `components`, `depends_on`) so they're additive. ✅

**Placeholder scan:** No "TBD/handle edge cases/similar to Task N" — every code step has complete code. ✅

**Type consistency:** `RepoContext` fields used identically across Tasks 4/6/9; `complete_json(system, user)` signature consistent across Tasks 5/6; `derive_todos(branch_status, open_prs)` consistent across Tasks 2/6; `generate_record(ctx, client, *, model=None)` consistent across Tasks 6/9; record field names match `schema.py` across Tasks 1/6/7/8. ✅

One known coupling to call out for the implementer: Task 6's `generated_at`/`source_commit`/`model` provenance fields and Task 1's `REQUIRED_STRING_FIELDS` must stay in lockstep — if you add a provenance field, add it to the validator too.
