agentC-web-resilience — Sprint 6

Sprint-Level Context

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
