# Sprint 9

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

Merge Order
1. agentA-search-fix
2. agentB-access-page
3. agentC-infra

Merge Verification
- python3 -m pytest tests/ -v

## agentA-search-fix

Objective
- Fix multi-word search so "voice processing" returns voice repos

Tasks
- In web/js/search.js, update the search/filter logic:
  - Split the query into individual terms on whitespace
  - A repo matches if ANY term appears in its name, description, or topics (OR logic)
  - Score repos higher when MORE terms match (rank by match count)
  - Keep existing exact-phrase match as highest priority (if full phrase matches, rank first)
  - Case-insensitive matching
- In web/js/app.js, update the search result count to show "N results for term1, term2" when multi-word
- Add fuzzy tolerance: if a term is >5 chars, also match if the term is a substring of a word (e.g., "process" matches "processing")
- Test cases to verify manually:
  - "voice processing" → returns voice repos (voice matches)
  - "s3 upload" → returns S3-presignedURL repo (s3 matches)
  - "presigned" → returns presigned-url repo (substring match)
  - "aws lambda" → returns repos with aws OR lambda topics
  - Single word "voice" → still works as before (9 results)

Acceptance Criteria
- Search "voice processing" returns voice-related repos (not 0 results)
- Search "s3 upload" returns S3/infrastructure repos
- Search "presigned" returns presigned-url repo
- Single-word searches still work correctly
- No JS errors in console

## agentB-access-page

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

## agentC-infra

Objective
- Fix venv symlink issue and clean up infrastructure

Tasks
- Fix B-012: In .sprint/scripts/ (the local project copy), find where .venv gets symlinked into worktrees and remove that behavior. If sprint-init.sh or sprint-tmux.sh symlinks .venv, change it to skip .venv. Add a comment: "# .venv is NOT symlinked — each worktree uses system python or creates its own venv"
- Update Makefile: add "deploy" target that runs aws s3 sync + cloudfront invalidation
- Add a simple smoke test in tests/test_smoke.py: verify ghps --help returns 0, verify ghps search --help returns 0
- Clean up: remove any .gitkeep files from web/data/ (we have real data now)

Acceptance Criteria
- python3 -m pytest tests/ -v shows 0 failures, 0 errors
- make deploy works (syncs to S3 + invalidates CloudFront)
- .venv is NOT symlinked into worktrees after sprint-init.sh runs
- No .gitkeep files in web/data/
