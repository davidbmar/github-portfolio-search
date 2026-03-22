# Sprint 9 — Agent Notes

*Started: 2026-03-22 16:37 UTC*

Phase 1 Agents: 3
- agentA-search-fix
- agentB-access-page
- agentC-infra

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentC-infra

*Completed: 2026-03-22 16:40 UTC*

### Files changed
- **`Makefile`** — Fixed `deploy` target to reference `deploy.sh` (was `scripts/deploy.sh` which didn't exist)
- **`tests/test_smoke.py`** — New file: smoke tests verifying `ghps --help` and `ghps search --help` return exit code 0
- **`web/data/.gitkeep`** — Deleted (real data files `repos.json` and `clusters.json` exist)

### Commands run
- `git pull origin main` — already up to date
- `python3 -m pytest tests/ -v` — **148 passed**, 1 pre-existing failure in `test_web_playwright.py` (agentA's domain)
- `git commit` + `git push -u origin HEAD`

### Notes / follow-on work
- **B-012** was already fixed in `sprint-init.sh` (lines 105-108) — `.venv` is explicitly skipped with explanatory comments
- The 1 failing test (`test_web_playwright.py::test_search_no_results`) is a pre-existing issue in the web search UI — the empty state message changed. This is in agentA's file scope (`web/js/search.js`)
- `deploy.sh` exists at repo root and performs S3 sync + CloudFront invalidation correctly; `make deploy` now points to it


---

## agentA-search-fix

*Completed: 2026-03-22 16:40 UTC*

### Files changed
- **`web/js/search.js`** — Rewrote `scoreRepo()` from AND to OR logic, added exact-phrase bonus (50 pts), multi-term match bonus, and `termMatches()` helper. Updated `search()` to pass full query string.
- **`web/js/app.js`** — Updated `renderSearchResults()` to display "N results for term1, term2" header for multi-word queries.
- **`docs/project-memory/sessions/S-2026-03-22-1640-sprint9-search-fix.md`** — Session doc.

### Commands run
- `git pull origin main` — already up to date
- `python3 -m pytest tests/ -v` — 147 passed
- `node -e ...` — JS sanity check of all 5 test cases
- `git push -u origin HEAD` — pushed

### Notes / follow-on work
- The fuzzy tolerance for terms >5 chars is already satisfied by `String.includes()` (e.g., "presigned" matches "presignedURL"). No additional fuzzy library was needed.
- If more sophisticated fuzzy matching is desired in the future (e.g., Levenshtein distance for typos), a dedicated library like Fuse.js could be added.


---

## agentB-access-page

*Completed: 2026-03-22 16:41 UTC*

**Files changed:**
- `web/js/app.js` — Updated tier info text in `renderAccessRequest()` to include gated access description
- `docs/project-memory/sessions/S-2026-03-22-1640-sprint9-access-page.md` — New session doc

**Commands run:**
- `git pull origin main` — Already up to date
- `python3 -m pytest tests/ -v` — 146 passed, 1 pre-existing failure
- `git push -u origin HEAD` — Pushed to `agentB-access-page`

**Notes / follow-on work:**
- Most of the Sprint 9 agentB tasks (access page route, form fields, CSS styles, OG meta tags, nav link) were already implemented in prior sprints. The only gap was the tier description text.
- Pre-existing test failure: `test_search_no_results` has a race condition where it finds the home page `.empty-state` ("Search to see all 42 repositories") instead of the search results empty state. This is in agentC's domain (`tests/`).

