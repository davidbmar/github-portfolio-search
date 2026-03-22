agentB-activity-stats — Sprint 11

Sprint-Level Context

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
