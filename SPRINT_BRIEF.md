# Sprint 14

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

Merge Order
1. agentC-data-pipeline
2. agentB-reindex-actions
3. agentA-freshness-ui

Merge Verification
- python3 -m pytest tests/ -v

## agentA-freshness-ui

Objective
- Add freshness badges and last-indexed timestamps to the web UI

Tasks
- Update web/js/app.js:
  - Add freshness badge to each repo card: "Updated today", "This week", "This month", "Stale (>30 days)"
  - Badge color: green (today), blue (this week), gray (this month), red (stale)
  - Calculate from the `updated_at` field in repos.json
  - Add "Last indexed" timestamp in the footer or stats section
  - Add sort option: "Recently Updated" should use actual dates, not alphabetical
- Update web/css/style.css:
  - Style freshness badges with appropriate colors
  - Badges should be small pills next to the repo language tag

Acceptance Criteria
- Each repo card shows a freshness badge
- Badges are color-coded by recency
- "Recently Updated" sort works correctly
- Mobile layout not broken by new badges
- Playwright test: visit davidbmar.com, verify badges render on repo cards

## agentB-reindex-actions

Objective
- Create GitHub Actions workflow for automated reindexing and deployment

Tasks
- Create `.github/workflows/reindex.yml`:
  - Trigger: manual dispatch (workflow_dispatch) + scheduled (weekly cron)
  - Steps: checkout, setup Python, install deps, run ghps index, run ghps export, deploy to S3
  - Use secrets: GITHUB_TOKEN, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
  - Include CloudFront invalidation after S3 sync
  - Add concurrency group to prevent overlapping runs
- Create `scripts/reindex.sh`:
  - Standalone script that runs: index → export → deploy
  - Reads GITHUB_TOKEN from env
  - Idempotent — safe to run multiple times
  - Prints summary: repos indexed, files exported, deploy status
- Update src/ghps/api.py:
  - Fix B-008/B-016: when no SQLite index exists, return `{"results": [], "error": "No index found. Run ghps index first."}` with 200 status instead of 500
  - Apply to /api/search, /api/clusters, /api/repos/<slug> endpoints
- Add tests for graceful error handling (no index → 200 with empty results)

Acceptance Criteria
- `scripts/reindex.sh` runs end-to-end locally (with GITHUB_TOKEN set)
- API returns empty results with helpful error when no index exists (not 500)
- GitHub Actions workflow is valid YAML (test with `act` or manual review)
- python3 -m pytest tests/ -v passes

## agentC-data-pipeline

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
