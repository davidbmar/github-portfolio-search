agentC-web-access — Sprint 5

Sprint-Level Context

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
