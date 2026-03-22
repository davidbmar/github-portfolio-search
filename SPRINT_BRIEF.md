# Sprint 4

Goal
- Build the public web UI for davidbmar.com with search and browse capabilities
- Fix Sprint 3 test failures (B-005, B-006)
- Deploy static site to S3/CloudFront

Constraints
- No two agents may modify the same files
- agentA owns bug fixes and static data export (tests/, src/ghps/export.py)
- agentB owns web UI frontend (web/index.html, web/css/, web/js/)
- agentC owns deployment pipeline and integration (deploy.sh, web/api-proxy.js)
- Use python3 for all commands
- Frontend must be vanilla JS (no build step) — served as static files from S3
- Mobile-responsive layout required

Merge Order
1. agentA-data-export
2. agentB-web-ui
3. agentC-deploy

Merge Verification
- python3 -m pytest tests/ -v

## agentA-data-export

Objective
- Fix test failures and build a static JSON data export for the web UI

Tasks
- Fix B-005: CLI test failures on missing index edge cases
- Fix B-006: JSON decode error in test_e2e.py
- Create src/ghps/export.py with:
  - export_static_bundle(store, output_dir) -> generates JSON files for static site
  - repos.json — all repos with metadata, description, language, topics, stars, url
  - clusters.json — capability clusters with repo names
  - search-index.json — pre-computed embeddings or search data for client-side search
- Add ghps export command to CLI: ghps export --db PATH --output web/data/
- Create tests/test_export.py

Acceptance Criteria
- python3 -m pytest tests/ -v passes with 0 failures
- ghps export produces valid JSON files in output directory
- repos.json contains all indexed repos with metadata

## agentB-web-ui

Objective
- Build a responsive search and browse UI for the public portfolio site

Tasks
- Create web/index.html — single page app with:
  - Search bar (prominent, centered on landing)
  - Search results with cards: repo name, description, language badge, stars, topics, relevance score
  - Capability cluster browse view (grid of cluster cards, click to expand)
  - Faceted filter sidebar: language, topics, stars range, last updated
  - Mobile responsive: stack layout, collapsible filters
- Create web/css/style.css — dark theme matching davidbmar.com placeholder aesthetic
- Create web/js/app.js — vanilla JS:
  - Fetch repos.json and clusters.json on load
  - Client-side search using pre-loaded data (filter + sort)
  - Hash routing: #/ (home), #/search?q=X, #/cluster/name
  - Debounced search input
- Create web/js/search.js — client-side search logic:
  - Text matching across repo name, description, topics, README excerpt
  - Score and rank results
  - Filter by facets

Acceptance Criteria
- index.html loads and shows search bar + cluster grid
- Typing a query shows filtered results
- Clicking a cluster shows repos in that cluster
- Layout works on mobile (375px viewport)
- Dark theme, clean typography

## agentC-deploy

Objective
- Build deployment pipeline to push web UI to S3/CloudFront at davidbmar.com

Tasks
- Create deploy.sh script that:
  - Runs ghps export to generate fresh data
  - Copies web/ files + data/ to a build directory
  - Uploads to S3 bucket davidbmar-com using aws s3 sync
  - Invalidates CloudFront cache (distribution E3RCY6XA80ANRT)
  - Prints the live URL
- Create web/data/.gitkeep (data dir for export output)
- Add deploy instructions to README.md
- Create a simple health check: web/health.json with version and last-deploy timestamp

Acceptance Criteria
- ./deploy.sh uploads files to S3 and invalidates CloudFront
- https://davidbmar.com shows the search UI after deploy
- deploy.sh is idempotent (safe to run multiple times)
