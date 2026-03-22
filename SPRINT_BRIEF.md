# Sprint 11

Goal
- Add visual portfolio analytics — help recruiters understand David's capabilities at a glance
- D3.js capability tree visualization
- Activity timeline showing recent work
- Portfolio stats and shareable social preview

Constraints
- No two agents may modify the same files
- agentA owns D3.js visualization (web/js/d3-viz.js — NEW FILE, web/index.html for D3 script tag)
- agentB owns activity timeline and stats (web/js/app.js, web/js/search.js)
- agentC owns social sharing and meta (web/css/style.css, web/index.html — only meta tags and CSS)
- Use python3 for all commands
- Do NOT commit .venv/ to git
- D3.js should be loaded via CDN (https://d3js.org/d3.v7.min.js)

Merge Order
1. agentA-d3-viz
2. agentB-activity-stats
3. agentC-social-meta

Merge Verification
- python3 -m pytest tests/ -v

## agentA-d3-viz

Objective
- Add an interactive D3.js circle-packing visualization of capability clusters

Tasks
- Create web/js/d3-viz.js:
  - Load clusters.json and repos.json data
  - Build a circle-packing layout where:
    - Outer circles = clusters (Voice & Speech, AI & Search, etc.)
    - Inner circles = repos, sized by stars (min size for 0-star repos)
    - Colors match cluster gradient theme from CSS
  - Add interactivity:
    - Hover on a repo circle → show tooltip with name and description
    - Click a repo circle → navigate to #/repo/<name>
    - Click a cluster circle → zoom into that cluster
  - Add a reset/zoom-out button
  - Responsive: scale to container width
- Update web/index.html: add <script src="https://d3js.org/d3.v7.min.js"></script> before app.js
- The visualization should be rendered in a container on the Clusters page (#/clusters)

Acceptance Criteria
- Playwright: navigate to #/clusters → circle-packing visualization renders
- Playwright: hover over a circle → tooltip shows repo name
- Playwright: click a repo circle → navigates to #/repo/<name>
- Visualization is responsive (works at 375px width)
- No JS errors in console

## agentB-activity-stats

Objective
- Add activity timeline and enhanced portfolio stats

Tasks
- In web/js/app.js, enhance the landing page:
  - Add "Recent Activity" section showing the 10 most recently updated repos
  - Each shows: repo name (linked to detail), last updated date, language badge
  - Sort by updated_at descending
- In web/js/app.js, enhance the Clusters page (#/clusters):
  - Add a stats summary above the clusters: total repos, most active cluster, most common language
  - Add a "Technology Distribution" section showing topic counts as a horizontal bar chart
  - Show top 10 topics with their repo counts
- In web/js/search.js:
  - Add sort options for search results: Relevance (default), Recently Updated, Name A-Z
  - Add a small dropdown or toggle above search results

Acceptance Criteria
- Playwright: landing page shows "Recent Activity" with 10 repos sorted by date
- Playwright: clusters page shows stats summary and topic distribution chart
- Playwright: search results can be sorted by Relevance, Recently Updated, or Name
- No JS errors in console

## agentC-social-meta

Objective
- Make the site look great when shared on social media and improve overall polish

Tasks
- Update web/css/style.css:
  - Style the D3 visualization container (min-height, dark background, border)
  - Style tooltips for D3 hover (dark tooltip with white text, rounded corners)
  - Style the "Recent Activity" section (compact card list)
  - Style sort dropdown for search results
  - Add a subtle page transition animation when navigating between routes
  - Ensure all new elements work at 375px mobile viewport
- Update web/index.html (meta tags only, do NOT modify script tags):
  - Update og:title to "David Mar — GitHub Portfolio Search"
  - Update og:description to "42 repositories across 6 capability areas. Explore voice AI, infrastructure, search tools, and more."
  - Add twitter:card meta tag (summary_large_image)
  - Add canonical URL meta tag

Acceptance Criteria
- Playwright: D3 viz has proper dark background and styled tooltips
- Playwright: Recent Activity section is compact and readable
- Playwright: mobile viewport (375px) — all new elements fit without horizontal scroll
- OG meta tags present in page source with accurate content
- No layout shifts or visual glitches during route transitions
