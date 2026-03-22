# Sprint 8

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

Merge Order
1. agentA-search-relevance
2. agentB-ui-polish
3. agentC-infra-fixes

Merge Verification
- python3 -m pytest tests/ -v

## agentA-search-relevance

Objective
- Improve search result quality with real data

Tasks
- In src/ghps/search.py, add title boosting: if query terms appear in repo name, boost score by 2x
- In src/ghps/search.py, add recency factor: repos updated in last 6 months get a 1.2x boost, last year 1.0x, older 0.8x
- In src/ghps/export.py, add "last_indexed" timestamp to repos.json metadata
- In src/ghps/export.py, sort repos by relevance score (stars + recency) not alphabetically
- Add a test in tests/test_search.py that verifies title boosting works (search for "presigned" should rank presigned-url repo first)
- Add a test that verifies recency boosting (recent repos ranked higher than stale ones, all else equal)

Acceptance Criteria
- python3 -m pytest tests/test_search.py -v passes with new relevance tests
- ghps search "presigned URL" returns S3-presignedURL repo as top result
- ghps search "voice" returns voice-related repos ranked by relevance
- repos.json includes last_indexed timestamp

## agentB-ui-polish

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

## agentC-infra-fixes

Objective
- Fix venv symlink issue and improve developer experience

Tasks
- Fix B-012: Update .sprint/scripts/sprint-init.sh (or the local copy) to NOT symlink .venv into worktrees. Instead, each worktree should create its own venv or use the system python. Add a comment explaining why.
- Add .env.example file with GITHUB_TOKEN=ghp_xxx placeholder (for F-001)
- Update scripts/index-and-export.sh to source .env if it exists (python-dotenv style)
- Add a test that verifies ghps CLI --help works without a venv (basic smoke test)
- Update Makefile: add "reindex" target that runs the full index-and-export pipeline

Acceptance Criteria
- python3 -m pytest tests/ -v shows 0 failures, 0 errors
- make reindex works when GITHUB_TOKEN is set
- .env.example exists with clear instructions
- After sprint-init.sh creates worktrees, .venv is NOT symlinked (verify manually)
