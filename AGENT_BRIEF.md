agentA-freshness-ui — Sprint 14

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
