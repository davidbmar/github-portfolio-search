agentB-access-page — Sprint 9

Sprint-Level Context

Goal
- CRITICAL: Fix F-005 — web search fails on multi-word queries ("voice processing" returns 0 results)
- Fix B-012 — .venv symlinks break after agent merges
- Add "Request Access" page skeleton for future gated tier
- Improve search result quality for recruiters

Constraints
- No two agents may modify the same files
- agentA owns web search fix (web/js/search.js, web/js/app.js)
- agentB owns access page and meta improvements (web/index.html, web/css/style.css)
- agentC owns infrastructure fixes (scripts/, .sprint/, Makefile, tests/)
- Use python3 for all commands
- Do NOT commit .venv/ to git


Objective
- Add a "Request Access" page and improve site metadata

Tasks
- Create the Request Access page in web/js/app.js (add route handler for #/access):
  - Show a form with: Name, Email, Reason for access (textarea)
  - Submit button (disabled for now — shows "Coming soon" message on submit)
  - Explain what gated access provides: "Full code search, file tree browsing, and detailed repository analysis"
  - Style with existing CSS variables
- Update web/index.html:
  - Ensure OG meta tags use real data: "42 repositories across 6 capability areas"
  - Add og:image pointing to a screenshot or placeholder
- Update web/css/style.css:
  - Style the access request form (consistent with existing dark theme)
  - Add form input styles: dark background, light text, blue accent border on focus
  - Style the "Coming soon" message as a friendly info card

Acceptance Criteria
- Playwright: navigate to https://davidbmar.com/#/access — form renders with 3 fields
- Playwright: click Submit — shows "Coming soon" message, no errors
- OG tags are present and accurate in page source
- Mobile layout works at 375px
