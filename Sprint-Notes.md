# Sprint 14 — Agent Notes

*Started: 2026-03-22 20:08 UTC*

Phase 1 Agents: 3
- agentA-freshness-ui
- agentB-reindex-actions
- agentC-data-pipeline

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentB-reindex-actions

*Completed: 2026-03-22 20:14 UTC*

### Files changed
- **`.github/workflows/reindex.yml`** (NEW) — GitHub Actions workflow with manual dispatch + weekly cron, Python setup, index/export/S3 deploy/CloudFront invalidation, concurrency group
- **`scripts/reindex.sh`** (NEW) — Standalone idempotent script: index → export → deploy with summary output
- **`src/ghps/api.py`** (MODIFIED) — Added `_is_no_table_error()` helper; `/api/search`, `/api/clusters`, `/api/repos/{slug}` now return `{"results": [], "error": "No index found. Run ghps index first."}` with 200 instead of 500 when no index exists
- **`tests/test_api_no_index.py`** (NEW) — 4 tests verifying graceful error handling on all three endpoints
- **`docs/project-memory/sessions/S-2026-03-22-2013-reindex-actions.md`** (NEW) — Session doc

### Commands run
- `python3 -m py_compile src/ghps/api.py` — compile check
- `python3 -m pytest tests/ -v` — 189 passed
- `git push -u origin HEAD` — pushed to `agentB-reindex-actions`

### Notes / follow-on work
- The `_is_no_table_error()` helper uses type-name checking (`"OperationalError" in type(exc).__name__`) because `pysqlite3.dbapi2.OperationalError` doesn't inherit from stdlib `sqlite3.OperationalError`. This is a pragmatic workaround for the dual-sqlite3 import pattern in `store.py`.
- `scripts/reindex.sh` gracefully skips deploy if AWS CLI is not installed, making it usable for local dev without AWS credentials.


---

## agentC-data-pipeline

*Completed: 2026-03-22 20:15 UTC*

### Files changed
- **`src/ghps/store.py`** — Added `indexed_at TEXT` column to repos table, auto-populated in `add_repo()`, added `get_index_stats()` method
- **`src/ghps/indexer.py`** — Added `dry_run` parameter to `index_repos()`/`index_user()`, try/except per-repo error handling, summary logging (indexed/failed/skipped)
- **`src/ghps/search.py`** — Added `indexed_at` and `freshness` fields to `SearchResult`, added `_freshness_label()` function (today/this_week/this_month/stale)
- **`tests/test_data_pipeline.py`** — New: 14 tests covering indexed_at storage, get_index_stats(), freshness labels, dry-run mode, error handling
- **`tests/test_search.py`** — Updated mock store helper to include `indexed_at` in metadata rows
- **`docs/project-memory/sessions/S-2026-03-22-2013-sprint14-data-pipeline.md`** — Session doc

### Commands run
- `git pull origin main`
- `python3 -m pytest tests/ -v` — 208 passed, 8 errors (pre-existing port conflicts in playwright tests)
- `git push -u origin HEAD`

### Notes / follow-on work
- The `--dry-run` flag is wired in `indexer.py` but not yet exposed as a CLI option in `cli.py`. The CLI is not owned by agentC per the brief constraints, but the indexer API fully supports it.
- Pre-existing test isolation issue: `test_web_playwright.py` fails with port-in-use errors (unrelated to this work).


---

## agentA-freshness-ui

*Completed: 2026-03-22 20:20 UTC*

```
```

