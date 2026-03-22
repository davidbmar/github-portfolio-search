agentC-data-pipeline — Sprint 14

Sprint-Level Context

Goal
- Add GitHub Actions workflow to auto-reindex and redeploy on push
- Add freshness badges to web UI showing when each repo was last indexed
- Fix API graceful error handling when no index exists (B-008/B-016)

Constraints
- No two agents may modify the same files
- agentA owns web UI changes (web/js/app.js, web/css/style.css)
- agentB owns GitHub Actions and indexing (`.github/workflows/reindex.yml` — NEW FILE, `scripts/reindex.sh` — NEW FILE, src/ghps/api.py)
- agentC owns data pipeline improvements (src/ghps/indexer.py, src/ghps/store.py, src/ghps/search.py)
- Use python3 for all commands
- Do NOT commit .venv/ or .env to git
- The site is static S3/CloudFront — no running server for webhooks


Objective
- Improve indexing reliability and add metadata for freshness tracking

Tasks
- Update src/ghps/store.py:
  - Add `indexed_at` timestamp column to repos table (datetime of when each repo was indexed)
  - Ensure `indexed_at` is populated during insert/update
  - Add method: `get_index_stats()` → returns { total_repos, last_indexed, oldest_repo }
- Update src/ghps/indexer.py:
  - Pass `indexed_at` timestamp when storing repos
  - Add `--dry-run` flag: show what would be indexed without making changes
  - Improve error handling: skip repos that fail to fetch (log warning, continue)
  - Print summary at end: N repos indexed, M failed, K skipped
- Update src/ghps/search.py:
  - Include `indexed_at` in search results metadata
  - Add `freshness` field to results: "today", "this_week", "this_month", "stale"
- Add tests for indexed_at storage, freshness calculation, and dry-run mode

Acceptance Criteria
- `indexed_at` timestamp stored for every repo during indexing
- `--dry-run` flag works (shows plan, no changes)
- Failed repos don't crash the indexer
- Freshness field appears in search results
- python3 -m pytest tests/ -v passes
