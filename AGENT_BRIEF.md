agentB-ui-polish — Sprint 8

Sprint-Level Context

Goal
- Search relevance tuning — make semantic search return better results with real data
- UX polish — make the site look professional for recruiters and hiring managers
- Fix B-012 — .venv symlinks break after agent merges

Constraints
- No two agents may modify the same files
- agentA owns search relevance (src/ghps/search.py, src/ghps/embeddings.py, src/ghps/export.py)
- agentB owns web UI polish (web/js/app.js, web/js/search.js, web/css/style.css, web/index.html)
- agentC owns infrastructure fixes (tests/, scripts/, .sprint/, Makefile, pyproject.toml)
- Use python3 for all commands
- Do NOT commit .venv/ to git


Objective
- Make davidbmar.com look professional — a recruiter should understand David's capabilities in 10 seconds

Tasks
- Update web/js/app.js:
  - Add portfolio stats on landing page: "N repositories indexed across M capability areas"
  - Add "Last updated: DATE" indicator from repos.json metadata
  - Show repo count per language in a small bar chart or stat row
- Update web/js/search.js:
  - Bold/highlight matched query terms in search result descriptions
  - Add "Related repos" section below search results (repos in same cluster)
  - Show relevance score as a visual bar instead of raw number
- Update web/css/style.css:
  - Improve card hover effects (subtle lift + shadow)
  - Better typography: increase line-height for readability
  - Add gradient accent to cluster cards matching cluster theme
  - Improve search result card layout — more whitespace, cleaner hierarchy
- Update web/index.html:
  - Update meta description with real portfolio stats
  - Ensure OG image and description work for social sharing

Acceptance Criteria
- Playwright: visit https://davidbmar.com — landing page shows repo count, cluster count, last updated
- Playwright: search for "voice" — results show highlighted terms, relevance bars
- Playwright: mobile viewport (375px) — all elements readable, no horizontal scroll
- No uncaught JS errors in console
