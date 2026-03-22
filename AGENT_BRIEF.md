agentA-d3-viz — Sprint 11

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
