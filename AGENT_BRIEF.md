agentB-web-ui — Sprint 4

Sprint-Level Context

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
