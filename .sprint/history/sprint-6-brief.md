# Sprint 6

Goal
- CRITICAL: Fix B-010 — davidbmar.com shows "Could not load data" because data files are empty
- Fix B-005, B-006 — remaining 4 test failures from Sprint 3
- Add sample data so the site works without a GitHub token
- Production hardening: proper error handling when data is missing

Constraints
- No two agents may modify the same files
- agentA owns data pipeline fixes (src/ghps/export.py, web/data/, scripts/)
- agentB owns test fixes and infrastructure (tests/, pyproject.toml, Makefile)
- agentC owns web UI error handling and resilience (web/js/app.js, web/js/search.js, web/index.html)
- Use python3 for all commands
- Do NOT commit .venv/ to git

Merge Order
1. agentA-data-pipeline
2. agentB-test-infra
3. agentC-web-resilience

Merge Verification
- python3 -m pytest tests/ -v

## agentA-data-pipeline

Objective
- Create working sample data and fix the export pipeline so davidbmar.com has content

Tasks
- Create web/data/repos.json with realistic sample data: 10 repos representing David's portfolio (e.g., audio-stream-transcription, presigned-url-s3, grassyknoll, FSM-generic, tool-telegram-whatsapp, bot-customerobsessed, traceable-searchable-adr-memory-index, github-portfolio-search, tool-s3-cloudfront-push, everyone-ai). Each repo: name, description, language, topics array, stars, html_url, updated_at
- Create web/data/clusters.json with 4 capability clusters: "Voice & Audio Processing", "Infrastructure & DevOps", "AI & Search", "Web Applications"
- Verify src/ghps/export.py produces valid JSON matching this schema
- Create scripts/generate-sample-data.py that produces realistic sample data
- Update deploy.sh to check for valid data files before deploying

Acceptance Criteria
- web/data/repos.json is valid JSON with 10+ repos
- web/data/clusters.json is valid JSON with 4+ clusters
- Playwright: visit file:///path/to/web/index.html — search shows results, clusters render

## agentB-test-infra

Objective
- Fix all remaining test failures and get to 0 failures / 0 errors

Tasks
- Fix B-005: test_cli.py TypeError on missing index — add try/except in cli.py for FileNotFoundError when DB doesn't exist, return helpful error message
- Fix B-006: test_e2e.py JSON decode error — ensure ghps search --format json outputs valid JSON even when no results found (output empty array, not error text)
- Add playwright to pyproject.toml [project.optional-dependencies] test group
- Create Makefile with targets: install, test, serve, index, export, deploy
- Remove or skip test_web_playwright.py tests if playwright browser not installed (use pytest.importorskip)

Acceptance Criteria
- python3 -m pytest tests/ -v shows 0 failures, 0 errors (playwright tests skipped if browser not installed)
- make test runs the full suite
- make install sets up the venv
- ghps search --format json returns valid JSON for empty results

## agentC-web-resilience

Objective
- Make the web UI handle missing/empty data gracefully and look professional

Tasks
- Update web/js/app.js:
  - Handle fetch errors gracefully: show "No data available — run ghps index to populate" instead of JSON parse error
  - Add retry button when data fails to load
  - Show sample data inline as fallback if fetch fails (embedded minimal dataset)
  - Add footer: "Powered by GitHub Portfolio Search — Built with Afterburner"
- Update web/js/search.js:
  - Handle empty repos array without crashing
  - Show "No repositories indexed yet" when data is empty
- Update web/css/style.css:
  - Style error states (friendly, not scary)
  - Add loading skeleton animation while data loads
  - Ensure footer stays at bottom
- Update web/index.html:
  - Add meta description and OG tags for social sharing
  - Add favicon (simple emoji or SVG)

Acceptance Criteria
- Playwright: visit site with empty data — shows friendly message, no JS errors in console
- Playwright: visit site with sample data — search works, clusters render
- Mobile layout works at 375px viewport
- No uncaught JS errors in console
