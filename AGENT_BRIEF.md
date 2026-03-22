agentC-social-meta — Sprint 11

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
