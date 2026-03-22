agentB-reindex-actions — Sprint 14

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
