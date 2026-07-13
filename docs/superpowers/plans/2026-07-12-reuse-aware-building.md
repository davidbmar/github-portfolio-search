# Reuse-Aware Building Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "scan before you build" mechanism — an MCP tool that surfaces existing repos relevant to what you're about to build (with provenance), and a ledger tool that records the reuse decision, accumulating the missing repo→repo graph.

**Architecture:** Pure logic lives in a new `src/ghps/reuse.py` (retrieval + provenance merge + ledger append). The MCP server (`src/ghps/mcp_server.py`) gets two thin handlers that call it: `portfolio_reuse_check` (read-only) and `portfolio_record_reuse` (the one writer, appends to `web/data/reuse-ledger.jsonl`). A skill + CLAUDE.md rule + a `UserPromptSubmit` hook make the check fire; `llms.txt` surfaces it to external agents. Canonical-block derivation is out of scope (v2, per ADR-0001).

**Tech Stack:** Python 3.9+, stdlib only (`json`, `re`, `pathlib`, `datetime`); existing `ghps.store.VectorStore`, `ghps.embeddings.EmbeddingPipeline`, `ghps.docsgen.search_docs`; MCP JSON-RPC over stdio; pytest.

## Global Constraints

- **Python >=3.9.** Every new module starts with `from __future__ import annotations`; use subscripted generics (`list[dict]`) only in annotations, never as runtime values.
- **No new third-party dependencies.** `reuse.py` is stdlib + existing `ghps.*` only.
- **Relations are exactly:** `reuse`, `extend`, `link`, `inspired`, `new`. Reject anything else.
- **Ledger path default:** `web/data/reuse-ledger.jsonl` (one JSON object per line, append-only).
- **Defaults:** `portfolio_reuse_check` → `k=5`, `min_score=0.5`.
- **Commits** use a human-readable subject and this body trailer:
  ```
  Session: S-2026-07-12-2332-reuse-aware-building
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```
- **Run tests with:** `python -m pytest <path> -v` from repo root (add `src` to path is handled by the test files' `sys.path.insert`).

---

### Task 1: Ledger writer + building-input resolver

**Files:**
- Create: `src/ghps/reuse.py`
- Test: `tests/test_reuse.py`

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces:
  - `RELATIONS: frozenset[str]` = `{"reuse","extend","link","inspired","new"}`
  - `load_building_text(building: str) -> tuple[str, str]` → `(text, source_label)`. If `building` is short enough to be a path AND names an existing file, returns that file's contents with label `"doc: <path>"`; otherwise returns `building` unchanged with label `"description: <first 80 chars>"`.
  - `record_reuse(ledger_path: str, built: str, reused: list[str], relation: str, note: str = "", session: str = "", ts: str | None = None) -> dict` → validates `relation`, appends one JSON line to `ledger_path` (creating parent dirs), returns the written record dict. Raises `ValueError` on bad relation or empty `built`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_reuse.py
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ghps.reuse import RELATIONS, load_building_text, record_reuse


def test_relations_are_exactly_five():
    assert RELATIONS == {"reuse", "extend", "link", "inspired", "new"}


def test_load_building_text_from_file(tmp_path):
    doc = tmp_path / "design.md"
    doc.write_text("streaming ASR with speaker diarization")
    text, source = load_building_text(str(doc))
    assert text == "streaming ASR with speaker diarization"
    assert source == f"doc: {doc}"


def test_load_building_text_from_description():
    text, source = load_building_text("a meeting notes summarizer")
    assert text == "a meeting notes summarizer"
    assert source == "description: a meeting notes summarizer"


def test_record_reuse_appends_jsonl(tmp_path):
    ledger = tmp_path / "reuse-ledger.jsonl"
    rec = record_reuse(
        str(ledger), built="meeting-summarizer", reused=["parakeet-asr-service"],
        relation="reuse", note="used /transcribe", session="S-x", ts="2026-07-12T00:00:00Z",
    )
    assert rec["built"] == "meeting-summarizer"
    assert rec["reused"] == ["parakeet-asr-service"]
    assert rec["relation"] == "reuse"
    lines = ledger.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == rec

    record_reuse(str(ledger), built="b2", reused=[], relation="new", note="nothing fit")
    assert len(ledger.read_text().splitlines()) == 2  # appends, not overwrites


def test_record_reuse_rejects_bad_relation(tmp_path):
    with pytest.raises(ValueError):
        record_reuse(str(tmp_path / "l.jsonl"), built="x", reused=[], relation="borrow")


def test_record_reuse_rejects_empty_built(tmp_path):
    with pytest.raises(ValueError):
        record_reuse(str(tmp_path / "l.jsonl"), built="", reused=[], relation="new")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_reuse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghps.reuse'`

- [ ] **Step 3: Write the minimal implementation**

```python
# src/ghps/reuse.py
"""Reuse-aware building — retrieval, provenance, and the reuse ledger.

See ADR-0001. Pure logic; the MCP server wraps these in thin handlers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

RELATIONS = frozenset({"reuse", "extend", "link", "inspired", "new"})


def load_building_text(building: str) -> tuple[str, str]:
    """Resolve the tool's `building` arg to (text, source_label).

    A short value that names an existing file is read as a design doc; anything
    else is treated as an inline description. The 400-char guard stops a long
    design-doc-passed-as-text from being probed as a filesystem path.
    """
    try:
        if len(building) < 400 and Path(building).is_file():
            return Path(building).read_text(), f"doc: {building}"
    except OSError:
        pass
    return building, f"description: {building[:80]}"


def record_reuse(
    ledger_path: str,
    built: str,
    reused: list[str],
    relation: str,
    note: str = "",
    session: str = "",
    ts: str | None = None,
) -> dict:
    """Append one reuse decision to the JSONL ledger; return the written record."""
    if not built:
        raise ValueError("built is required")
    if relation not in RELATIONS:
        raise ValueError(f"relation must be one of {sorted(RELATIONS)}, got {relation!r}")

    record = {
        "ts": ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "built": built,
        "reused": list(reused or []),
        "relation": relation,
        "note": note,
        "session": session,
    }
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(record) + "\n")
    return record
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_reuse.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/reuse.py tests/test_reuse.py
git commit -m "$(printf 'feat(reuse): reuse ledger writer + building-input resolver\n\nSession: S-2026-07-12-2332-reuse-aware-building\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 2: `reuse_check` — retrieval + provenance merge

**Files:**
- Modify: `src/ghps/reuse.py` (append functions)
- Test: `tests/test_reuse.py` (append a class)

**Interfaces:**
- Consumes: `ghps.docsgen.search_docs.search_docs`; a `store` exposing `.search(query_vec, limit) -> list[rows]` where each row supports `row["repo_name"]`, `row["distance"]`, `row["text"]`; an `embedder` exposing `.embed_text(text) -> list[float]`.
- Produces:
  - `reuse_check(store, embedder, projects: list[dict], building: str, k: int = 5, min_score: float = 0.5) -> dict` → `{"source": str, "verdict": "candidates"|"greenfield", "candidates": [ {repo, score, one_liner, repo_url, reuse_tags, patterns, how_to_apply, why: {matched_fields, snippet}} ]}`. Candidates are embedding hits with `score >= min_score`, ranked by score desc; each joined with its docs-feed record (keyed by `repo_name == slug`) and annotated with the fields that matched the query (`search_docs`) plus the embedding snippet.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_reuse.py
import math
from ghps.store import EMBEDDING_DIM, VectorStore


def _fake_embedding(seed: int) -> list[float]:
    return [math.sin(seed * 0.1 + i * 0.01) * 0.5 for i in range(EMBEDDING_DIM)]


class _FakeEmbedder:
    def embed_text(self, text: str) -> list[float]:
        return _fake_embedding(hash(text) % 1000)


_PROJECTS = [
    {
        "slug": "parakeet-asr-service", "title": "Parakeet ASR",
        "one_liner": "Streaming speech-to-text service.",
        "repo_url": "https://github.com/u/parakeet-asr-service",
        "tech": ["python", "nemo"], "reuse_tags": ["asr", "streaming-transcription"],
        "patterns": ["websocket audio ingestion"], "how_to_apply": "POST audio to /transcribe",
    },
    {
        "slug": "web-dashboard", "title": "Web Dashboard",
        "one_liner": "React monitoring dashboard.",
        "repo_url": "https://github.com/u/web-dashboard",
        "tech": ["javascript", "react"], "reuse_tags": ["charts"],
        "patterns": [], "how_to_apply": "",
    },
]


class _FakeStore:
    """Returns canned rows so the merge logic is tested without real vectors."""
    def __init__(self, rows):
        self._rows = rows

    def search(self, query_vec, limit=10):
        return self._rows[:limit]


def _row(repo_name, distance, text):
    return {"repo_name": repo_name, "distance": distance, "text": text}


def test_reuse_check_returns_candidates_with_provenance():
    from ghps.reuse import reuse_check
    store = _FakeStore([
        _row("parakeet-asr-service", 0.2, "streaming ASR pipeline README excerpt"),
        _row("web-dashboard", 0.7, "react dashboard charts"),
    ])
    out = reuse_check(store, _FakeEmbedder(), _PROJECTS,
                      "streaming speech to text transcription", k=5, min_score=0.5)
    assert out["verdict"] == "candidates"
    assert out["source"].startswith("description:")
    top = out["candidates"][0]
    assert top["repo"] == "parakeet-asr-service"      # 1.0-0.2 = 0.8 >= 0.5
    assert top["score"] == 0.8
    assert top["reuse_tags"] == ["asr", "streaming-transcription"]
    assert top["how_to_apply"] == "POST audio to /transcribe"
    assert "snippet" in top["why"] and top["why"]["snippet"]
    assert isinstance(top["why"]["matched_fields"], list)
    # web-dashboard scored 0.3 (< min_score) → filtered out
    assert [c["repo"] for c in out["candidates"]] == ["parakeet-asr-service"]


def test_reuse_check_greenfield_when_nothing_passes_threshold():
    from ghps.reuse import reuse_check
    store = _FakeStore([_row("web-dashboard", 0.9, "react dashboard")])  # score 0.1
    out = reuse_check(store, _FakeEmbedder(), _PROJECTS, "quantum compiler", min_score=0.5)
    assert out["verdict"] == "greenfield"
    assert out["candidates"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reuse.py -k reuse_check -v`
Expected: FAIL — `ImportError: cannot import name 'reuse_check'`

- [ ] **Step 3: Write the implementation**

```python
# append to src/ghps/reuse.py

def _embedding_candidates(store, embedder, query: str, k: int) -> list[dict]:
    """Nearest repos by embedding, deduped to best score per repo."""
    vec = embedder.embed_text(query)
    raw = store.search(vec, limit=k * 3)
    best: dict[str, dict] = {}
    for row in raw:
        repo = row["repo_name"]
        score = round(1.0 - row["distance"], 4)
        if repo not in best or score > best[repo]["score"]:
            best[repo] = {"repo": repo, "score": score, "snippet": (row["text"] or "")[:200]}
    return sorted(best.values(), key=lambda c: -c["score"])[:k]


def reuse_check(store, embedder, projects: list[dict], building: str,
                k: int = 5, min_score: float = 0.5) -> dict:
    """Surface existing repos relevant to what's about to be built, with provenance."""
    from ghps.docsgen.search_docs import search_docs

    text, source = load_building_text(building)
    by_slug = {p.get("slug", ""): p for p in projects}
    matched_by_slug = {h["slug"]: h["matched"] for h in search_docs(projects, text, limit=50)}

    candidates = []
    for cand in _embedding_candidates(store, embedder, text, k):
        if cand["score"] < min_score:
            continue
        rec = by_slug.get(cand["repo"], {})
        candidates.append({
            "repo": cand["repo"],
            "score": cand["score"],
            "one_liner": rec.get("one_liner", ""),
            "repo_url": rec.get("repo_url", ""),
            "reuse_tags": rec.get("reuse_tags", []),
            "patterns": rec.get("patterns", []),
            "how_to_apply": rec.get("how_to_apply", ""),
            "why": {
                "matched_fields": matched_by_slug.get(cand["repo"], []),
                "snippet": cand["snippet"],
            },
        })

    return {
        "source": source,
        "verdict": "candidates" if candidates else "greenfield",
        "candidates": candidates,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_reuse.py -v`
Expected: PASS (7 tests total)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/reuse.py tests/test_reuse.py
git commit -m "$(printf 'feat(reuse): reuse_check retrieval + provenance merge\n\nSession: S-2026-07-12-2332-reuse-aware-building\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 3: Wire both tools into the MCP server

**Files:**
- Modify: `src/ghps/mcp_server.py` (add 2 TOOLS entries; add 2 handlers; thread `ledger_path` through `handle_message`, `run_stdio`, `main`)
- Modify: `tests/test_mcp.py` (update tool-count 5→7 and name set; add reuse-tool tests)

**Interfaces:**
- Consumes: `ghps.reuse.reuse_check`, `ghps.reuse.record_reuse`.
- Produces: two new MCP tools — `portfolio_reuse_check {building, k?, min_score?}` and `portfolio_record_reuse {built, reused[], relation, note?, session?}`. `handle_message(msg, store, embedder, docs_feed="web/data/projects.json", ledger_path="web/data/reuse-ledger.jsonl")`.

- [ ] **Step 1: Update the failing tool-definition tests**

In `tests/test_mcp.py`, change `TestToolDefinitions.test_tool_count` to `assert len(TOOLS) == 7`, add `"portfolio_reuse_check"` and `"portfolio_record_reuse"` to the `test_tool_names` set, and update `TestMCPProtocol.test_tools_list` (`len(tools) == 7`; assert both new names present). Then append:

```python
# tests/test_mcp.py — new class
class TestReuseTools:
    def _feed(self, tmp_path):
        feed = tmp_path / "projects.json"
        feed.write_text(json.dumps({"projects": [{
            "slug": "ml-pipeline", "title": "ML Pipeline",
            "one_liner": "Data pipeline.", "repo_url": "https://github.com/u/ml-pipeline",
            "tech": ["python"], "reuse_tags": ["machine-learning"],
            "patterns": [], "how_to_apply": "import it",
        }]}))
        return str(feed)

    def test_reuse_check_returns_verdict(self, mcp_store, embedder, tmp_path):
        msg = {"jsonrpc": "2.0", "id": 80, "method": "tools/call", "params": {
            "name": "portfolio_reuse_check",
            "arguments": {"building": "machine learning data pipeline"}}}
        resp = handle_message(msg, mcp_store, embedder, self._feed(tmp_path),
                              str(tmp_path / "ledger.jsonl"))
        out = json.loads(resp["result"]["content"][0]["text"])
        assert out["verdict"] in ("candidates", "greenfield")
        assert "candidates" in out and "source" in out

    def test_record_reuse_writes_ledger(self, mcp_store, embedder, tmp_path):
        ledger = tmp_path / "ledger.jsonl"
        msg = {"jsonrpc": "2.0", "id": 81, "method": "tools/call", "params": {
            "name": "portfolio_record_reuse",
            "arguments": {"built": "x", "reused": ["ml-pipeline"],
                          "relation": "reuse", "note": "used it"}}}
        resp = handle_message(msg, mcp_store, embedder, self._feed(tmp_path), str(ledger))
        rec = json.loads(resp["result"]["content"][0]["text"])
        assert rec["relation"] == "reuse"
        assert ledger.read_text().count("\n") == 1

    def test_record_reuse_bad_relation_is_error(self, mcp_store, embedder, tmp_path):
        msg = {"jsonrpc": "2.0", "id": 82, "method": "tools/call", "params": {
            "name": "portfolio_record_reuse",
            "arguments": {"built": "x", "reused": [], "relation": "borrow"}}}
        resp = handle_message(msg, mcp_store, embedder, self._feed(tmp_path),
                              str(tmp_path / "l.jsonl"))
        assert resp["result"].get("isError") is True
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mcp.py -v`
Expected: FAIL — tool count is 5 not 7; `Unknown tool: portfolio_reuse_check`.

- [ ] **Step 3: Implement the wiring**

Append two entries to the `TOOLS` list in `src/ghps/mcp_server.py`:

```python
    {
        "name": "portfolio_reuse_check",
        "description": (
            "BEFORE building something new, scan the portfolio for existing repos to "
            "reuse/extend/link/take inspiration from. Accepts a short description OR a "
            "path to a design doc/plan. Returns ranked candidates with provenance "
            "(why each matched + score) or verdict 'greenfield' when nothing is close."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "building": {"type": "string", "description": "What you're about to build — a description or a path to a design doc/plan"},
                "k": {"type": "integer", "description": "Max candidates (default 5)", "default": 5},
                "min_score": {"type": "number", "description": "Similarity floor 0-1 (default 0.5)", "default": 0.5},
            },
            "required": ["building"],
        },
    },
    {
        "name": "portfolio_record_reuse",
        "description": (
            "Record a reuse decision after a reuse_check, building the repo→repo reuse "
            "graph. relation is one of reuse|extend|link|inspired|new. Use 'new' with a "
            "note when nothing fit (records why, so it isn't re-litigated later)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "built": {"type": "string", "description": "Slug/name of the thing being built"},
                "reused": {"type": "array", "items": {"type": "string"}, "description": "Repo names reused (empty for relation=new)"},
                "relation": {"type": "string", "enum": ["reuse", "extend", "link", "inspired", "new"]},
                "note": {"type": "string", "description": "One line on how/why"},
                "session": {"type": "string", "description": "Session ID, if any"},
            },
            "required": ["built", "relation"],
        },
    },
```

Add two handlers (near the other `_handle_*` functions):

```python
def _handle_portfolio_reuse_check(store: Any, embedder: Any, docs_feed: str, args: dict) -> dict:
    from ghps.docsgen.search_docs import load_feed
    from ghps.reuse import reuse_check

    building = args.get("building", "")
    if not building:
        raise ValueError("building is required")
    projects = load_feed(docs_feed)
    return reuse_check(
        store, embedder, projects, building,
        k=args.get("k", 5), min_score=args.get("min_score", 0.5),
    )


def _handle_portfolio_record_reuse(ledger_path: str, args: dict) -> dict:
    from ghps.reuse import record_reuse

    return record_reuse(
        ledger_path,
        built=args.get("built", ""),
        reused=args.get("reused", []),
        relation=args.get("relation", ""),
        note=args.get("note", ""),
        session=args.get("session", ""),
    )
```

Change `handle_message`'s signature and dispatch:

```python
def handle_message(
    msg: dict,
    store: Any,
    embedder: Any,
    docs_feed: str = "web/data/projects.json",
    ledger_path: str = "web/data/reuse-ledger.jsonl",
) -> dict | None:
```

In the `tools/call` block, add before the `else`:

```python
            elif tool_name == "portfolio_reuse_check":
                result = _handle_portfolio_reuse_check(store, embedder, docs_feed, arguments)
            elif tool_name == "portfolio_record_reuse":
                result = _handle_portfolio_record_reuse(ledger_path, arguments)
```

Thread `ledger_path` through the runner:

```python
def run_stdio(db_path: str, docs_feed: str = "web/data/projects.json",
              ledger_path: str = "web/data/reuse-ledger.jsonl") -> None:
```
- Inside `run_stdio`, pass it: `response = handle_message(msg, store, embedder, docs_feed, ledger_path)`.
- In `main()`, add the arg and pass it:
```python
    parser.add_argument(
        "--reuse-ledger", type=str, default="web/data/reuse-ledger.jsonl",
        help="Path to the reuse-decision ledger (default: web/data/reuse-ledger.jsonl)",
    )
    ...
    run_stdio(args.db, args.docs_feed, args.reuse_ledger)
```

- [ ] **Step 4: Run the full MCP + reuse suites**

Run: `python -m pytest tests/test_mcp.py tests/test_reuse.py -v`
Expected: PASS (all, including the updated count and the 3 new reuse-tool tests)

- [ ] **Step 5: Commit**

```bash
git add src/ghps/mcp_server.py tests/test_mcp.py
git commit -m "$(printf 'feat(mcp): expose portfolio_reuse_check + portfolio_record_reuse\n\nSession: S-2026-07-12-2332-reuse-aware-building\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 4: Reuse protocol — skill + CLAUDE.md rule

**Files:**
- Create: `.claude/skills/reuse-check/SKILL.md`
- Modify: `CLAUDE.md` (add a "Reuse-Aware Building" rule near the top of the workflow rules)

**Interfaces:**
- Consumes: the two MCP tools from Task 3.
- Produces: a documented habit; no code.

- [ ] **Step 1: Write the skill**

```markdown
<!-- .claude/skills/reuse-check/SKILL.md -->
---
name: reuse-check
description: Use BEFORE building any new component, feature, service, or script — scans the portfolio for existing repos to reuse/extend/link/take inspiration from, then records the decision. Triggers on "let's build", "create a new", "add a feature", "implement".
---

# Reuse Check — scan before you build

Before writing a new component, you MUST scan what already exists.

1. Call `portfolio_reuse_check(building=<description or path to the design doc/plan>)`.
2. If `verdict == "candidates"`, present the top matches to the user with their
   provenance ("surfaced X because your design doc mentions Y; it has reuse_tags [...]").
   Ask/decide: **reuse** (use as-is) · **extend** (build on top) · **link**
   (companion/see-also) · **inspired** (borrow the pattern) · **new** (nothing fit).
3. After the decision, call
   `portfolio_record_reuse(built=<slug>, reused=[...], relation=<one of above>, note=<one line>)`.
   For `new`, pass `reused=[]` and a note saying why nothing fit — that negative
   evidence is as valuable as a positive edge.

Skip only for trivial edits with no new component. When in doubt, run the check.
```

- [ ] **Step 2: Add the CLAUDE.md rule**

Insert after the "## Your Workflow" heading in `CLAUDE.md`:

```markdown
### 0. Reuse-Aware Building (do this FIRST)

Before building any new component/feature/service/script, run the `reuse-check`
skill: call `portfolio_reuse_check` with a description or the design-doc path,
weigh the surfaced candidates (reuse/extend/link/inspired/new), then record the
choice with `portfolio_record_reuse`. This builds the repo→repo reuse graph
(`web/data/reuse-ledger.jsonl`). See ADR-0001.
```

- [ ] **Step 3: Verify the skill is discoverable**

Run: `test -f .claude/skills/reuse-check/SKILL.md && grep -q "reuse-check" CLAUDE.md && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/reuse-check/SKILL.md CLAUDE.md
git commit -m "$(printf 'feat(reuse): reuse-check skill + CLAUDE.md scan-before-build rule\n\nSession: S-2026-07-12-2332-reuse-aware-building\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 5: Build-intent hook (the can't-forget backstop)

**Files:**
- Modify: `.claude/settings.json` (add a `UserPromptSubmit` hook)
- Create: `.claude/hooks/reuse-reminder.sh`

**Interfaces:**
- Consumes: nothing (pure shell); nudges toward the Task 4 skill.
- Produces: a deterministic reminder injected when a prompt looks like build-intent.

- [ ] **Step 1: Write the hook script**

```bash
# .claude/hooks/reuse-reminder.sh
#!/usr/bin/env bash
# Injects a reuse-check reminder when the user's prompt looks like build-intent.
# Reads the hook JSON on stdin; emits additionalContext (non-blocking) on a match.
input=$(cat)
prompt=$(printf '%s' "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null)
if printf '%s' "$prompt" | grep -qiE "\b(build|create|implement|add) (a |an |the )?(new )?(feature|component|service|tool|script|endpoint|module)"; then
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"Reuse check: before building this, run portfolio_reuse_check(building=...) and record the decision with portfolio_record_reuse (see the reuse-check skill / ADR-0001)."}}'
fi
```

Make it executable: `chmod +x .claude/hooks/reuse-reminder.sh`

- [ ] **Step 2: Register the hook in `.claude/settings.json`**

Add (merging into any existing `hooks` block — do not clobber existing hooks):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": ".claude/hooks/reuse-reminder.sh" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 3: Verify the trigger fires (and stays quiet otherwise)**

Run:
```bash
echo '{"prompt":"let us build a new transcription service"}' | .claude/hooks/reuse-reminder.sh
echo '{"prompt":"what time is it"}' | .claude/hooks/reuse-reminder.sh; echo "<-- (empty = quiet)"
```
Expected: first prints the `additionalContext` JSON; second prints nothing.

- [ ] **Step 4: Commit**

```bash
git add .claude/settings.json .claude/hooks/reuse-reminder.sh
git commit -m "$(printf 'feat(reuse): build-intent hook nudges the reuse check\n\nSession: S-2026-07-12-2332-reuse-aware-building\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 6: Surface in llms.txt + final wiring

**Files:**
- Modify: `web/llms.txt` (register the reuse tools + constellation.json)
- Modify: `docs/project-memory/sessions/S-2026-07-12-2332-reuse-aware-building.md` (fill Changes Made / Links)

**Interfaces:**
- Consumes: everything above.
- Produces: external-agent discoverability.

- [ ] **Step 1: Edit `web/llms.txt`**

Under "## Query interface for agents", add:

```markdown
MCP server `ghps-mcp` also exposes, for reuse-aware building:
- `portfolio_reuse_check(building)` — before building something new, get existing
  repos to reuse/extend/link/take inspiration from, with provenance (why each matched).
- `portfolio_record_reuse(built, reused, relation, note)` — record the decision;
  builds the repo→repo reuse graph.

Precomputed portfolio map (read instead of re-deriving):
https://davidbmar.com/data/constellation.json — every repo as a star, clusters,
similarity threads, centrality, and reuse tags.
```

- [ ] **Step 2: Verify**

Run: `grep -q "portfolio_reuse_check" web/llms.txt && grep -q "constellation.json" web/llms.txt && echo OK`
Expected: `OK`

- [ ] **Step 3: Run the whole test suite**

Run: `python -m pytest tests/test_reuse.py tests/test_mcp.py -v`
Expected: PASS (no regressions)

- [ ] **Step 4: Update the session doc + commit**

Fill "Changes Made" and "Links" in the session doc, then:

```bash
git add web/llms.txt docs/project-memory/sessions/S-2026-07-12-2332-reuse-aware-building.md
git commit -m "$(printf 'feat(reuse): surface reuse tools + constellation in llms.txt\n\nSession: S-2026-07-12-2332-reuse-aware-building\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

- [ ] **Step 5: Deploy note (not automated here)**

`web/llms.txt` and (later) `web/data/reuse-ledger.jsonl` ship via `reindex.yml`'s
`aws s3 sync web/`. No new deploy step needed — the ledger will sync once it exists.
Open PR to `main`; deploy runs on merge / next nightly.

---

## Self-Review

**Spec coverage (ADR-0001 → task):**
- Unit A `portfolio_reuse_check` (doc-or-text input, provenance, threshold, greenfield) → Tasks 1 (resolver), 2 (retrieval+provenance), 3 (MCP wiring). ✓
- Unit B `portfolio_record_reuse` + `reuse-ledger.jsonl` (5 relations, append-only) → Tasks 1, 3. ✓
- Unit C protocol (skill + CLAUDE.md) → Task 4. ✓
- Unit D hook (UserPromptSubmit build-intent) → Task 5. ✓
- Unit E llms.txt + constellation surfacing → Task 6. ✓
- Deferred v2 (ledger→constellation edges, canonical derivation) → correctly absent. ✓

**Placeholder scan:** No "TBD"/"handle edge cases"/"write tests for the above" — every code step shows complete code; every test step shows the assertions. ✓

**Type consistency:** `record_reuse(ledger_path, built, reused, relation, note, session, ts)` and `reuse_check(store, embedder, projects, building, k, min_score) -> {source, verdict, candidates:[{repo, score, one_liner, repo_url, reuse_tags, patterns, how_to_apply, why:{matched_fields, snippet}}]}` are used identically across Tasks 2 and 3. `RELATIONS` set is identical in reuse.py, the tool `enum`, and tests. `handle_message` gains `ledger_path` consistently in signature, dispatch, `run_stdio`, and `main`. ✓
