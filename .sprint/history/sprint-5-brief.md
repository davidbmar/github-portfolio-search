# Sprint 5

Goal
- Deploy the web UI to davidbmar.com (fix B-009)
- Fix remaining test failures (B-005, B-006)
- Add data export pipeline so the site has real content
- Begin gated access foundation (access request UI)

Constraints
- No two agents may modify the same files
- agentA owns deploy pipeline and bug fixes (deploy.sh, tests/test_cli.py, tests/test_e2e.py, src/ghps/cli.py)
- agentB owns data indexing and export (src/ghps/export.py, src/ghps/indexer.py, scripts/)
- agentC owns web UI improvements and access request page (web/)
- Use python3 for all commands
- Do NOT commit .venv/ or node_modules/ to git

Merge Order
1. agentA-deploy-fixes
2. agentB-index-export
3. agentC-web-access

Merge Verification
- python3 -m pytest tests/ -v

## agentA-deploy-fixes

Objective
- Fix test failures and create a working deploy script for davidbmar.com

Tasks
- Fix B-005: test_cli.py failures on missing index — add proper error handling in cli.py for when index DB doesn't exist
- Fix B-006: test_e2e.py JSON decode error — fix CLI --format json to output valid JSON
- Create deploy.sh in project root:
  - Check for web/ directory
  - If src/ghps/export.py exists, run ghps export --output web/data/
  - Run: aws s3 sync web/ s3://davidbmar-com/ --delete --exclude "*.pyc"
  - Run: aws cloudfront create-invalidation --distribution-id E3RCY6XA80ANRT --paths "/*"
  - Print: "Deployed to https://davidbmar.com"
- Make deploy.sh executable (chmod +x)
- Create tests/test_deploy.py — verify deploy.sh exists, is executable, has correct bucket name

Acceptance Criteria
- python3 -m pytest tests/test_cli.py tests/test_e2e.py -v passes with 0 failures
- ./deploy.sh runs without errors (when AWS credentials are available)
- Playwright test: after deploy, https://davidbmar.com shows search UI not placeholder

## agentB-index-export

Objective
- Create a working index + export pipeline so the web UI has real data

Tasks
- Verify src/ghps/export.py works end-to-end:
  - export_static_bundle should produce repos.json, clusters.json in output dir
  - If export.py is broken or incomplete, fix it
- Create scripts/index-and-export.sh:
  - Set up venv if missing
  - Run ghps index davidbmar --db .ghps/index.db (requires GITHUB_TOKEN)
  - Run ghps export --db .ghps/index.db --output web/data/
  - Print summary: N repos indexed, M clusters generated
- Add sample/mock data to web/data/ for development:
  - web/data/repos.json with 5 sample repos (for testing without GitHub token)
  - web/data/clusters.json with 2 sample clusters
- Update .gitignore: add .ghps/ (index database)

Acceptance Criteria
- web/data/repos.json exists with valid JSON (sample or real data)
- web/data/clusters.json exists with valid JSON
- scripts/index-and-export.sh is executable and documents the pipeline
- ghps export --output web/data/ produces valid JSON files

## agentC-web-access

Objective
- Improve web UI with real data loading and an access request page

Tasks
- Update web/js/app.js to:
  - Fetch web/data/repos.json and web/data/clusters.json on page load
  - Display repos in search results cards
  - Display clusters as clickable category cards on the landing page
  - Show "No results" when search returns empty
  - Add loading spinner while data loads
- Update web/index.html:
  - Add navigation: Home | Search | Clusters | Request Access
  - Add an "Request Access" page/section with:
    - Name input, email input, reason textarea
    - Submit button (posts to /api/access/request or shows "coming soon" message)
    - "Public tier — browse clusters and search descriptions. Request full access for code snippets."
- Update web/css/style.css:
  - Style result cards: repo name, description, language badge, stars count, topics
  - Style cluster cards: cluster name, repo count, representative repos
  - Mobile responsive: 375px viewport test
- Test with Playwright: verify search shows results from repos.json, clusters render

Acceptance Criteria
- Landing page shows cluster cards from clusters.json
- Search filters repos from repos.json
- Request Access section is visible with form fields
- Mobile layout works (375px viewport)
