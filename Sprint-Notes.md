# Sprint 1 — Agent Notes

*Started: 2026-03-22 04:58 UTC*

Phase 1 Agents: 3
- agentA-github-api
- agentB-embedding-store
- agentC-search-cli

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentA-github-api

*Completed: 2026-03-22 05:01 UTC*

## Files changed

| File | Action |
|------|--------|
| `pyproject.toml` | Created — project config with deps (requests, sentence-transformers, sqlite-vec, click, pytest) |
| `src/ghps/__init__.py` | Created — package init with `__version__ = "0.1.0"` |
| `src/ghps/github_client.py` | Created — GitHub API client with `fetch_repos`, `fetch_readme`, `fetch_top_files` |
| `tests/__init__.py` | Created — test package init |
| `tests/test_github_client.py` | Created — 10 unit tests (all mocked, no real API calls) |
| `.env.example` | Created — `GITHUB_TOKEN=ghp_xxx` template |
| `docs/project-memory/sessions/S-2026-03-22-0501-github-api-client.md` | Created — session doc |

## Commands run

- `git pull origin main` — already up to date
- `python3 -m venv .venv` + `pip install requests pytest`
- `PYTHONPATH=src python3 -m pytest tests/test_github_client.py -v` — **10 passed**
- `git commit` + `git push -u origin HEAD` — pushed to `agentA-github-api`

## Notes / follow-on work

- **No retry/backoff**: `fetch_top_files` and other calls don't handle rate limiting. For users with many repos + many files, GitHub's 5000 req/hr could be hit. Consider adding exponential backoff.
- **No file count limit**: `fetch_top_files` fetches ALL matching files. Large repos could return hundreds of files. May want a `max_files` parameter.
- **Python 3.9**: The system has Python 3.9, so `requires-python` was set to `>=3.9`. `from __future__ import annotations` handles forward-compatible type hints.


---

## agentC-search-cli

*Completed: 2026-03-22 05:02 UTC*

```
All tasks complete. Here's the summary:

---

## Files Changed

| File | Action |
|---|---|
| `src/ghps/search.py` | **Created** — SearchEngine class with dedup + ranking |
| `src/ghps/cli.py` | **Created** — Click CLI (`ghps search`, `ghps index`) |
| `src/ghps/__init__.py` | **Created** — minimal package init |
| `pyproject.toml` | **Created** — project config with `[project.scripts]` entry |
| `tests/test_search.py` | **Created** — 11 unit tests |
| `tests/__init__.py` | **Created** — test package init |
| `docs/project-memory/sessions/S-2026-03-22-0501-search-cli.md` | **Created** — session doc |

## Commands Run

- `git pull origin main` — synced with remote
- `python3 -m pip install click pytest` — installed dependencies
- `PYTHONPATH=src python3 -m pytest tests/test_search.py -v` — **11 passed**
- `git commit` / `git push -u origin HEAD` — committed and pushed

## Notes / Follow-on Work

1. **Merge conflict on `pyproject.toml`**: agentA also creates this file. During merge (A→B→C), agentA's version should be the base — the `[project.scripts]` section from this branch needs to be added.
2. **Merge conflict on `src/ghps/__init__.py`**: agentA owns this file. This branch's minimal version should be replaced by agentA's during merge.
3. **VectorStore.search() contract**: SearchEngine assumes the store returns `list[dict]` with keys `repo_name`, `text`, `score`, `source`, `url`. This must match agentB's actual VectorStore implementation — verify during integration.
```

