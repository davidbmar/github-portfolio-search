# Sprint 5 — Agent Notes

*Started: 2026-03-22 06:37 UTC*

Phase 1 Agents: 3
- agentA-deploy-fixes
- agentB-index-export
- agentC-web-access

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentA-deploy-fixes

*Completed: 2026-03-22 06:39 UTC*

**Files changed:**
- `deploy.sh` — rewritten to match sprint 5 spec (check web/ dir, conditional ghps export, s3 sync with `--exclude *.pyc`, CloudFront invalidation)
- `tests/test_deploy.py` — new file: 6 tests verifying deploy.sh exists, is executable, has correct bucket name, CloudFront distribution ID, web/ reference, and .pyc exclusion

**Commands run:**
- `git pull origin main` — already up to date
- `python3 -m pytest tests/test_cli.py tests/test_e2e.py tests/test_deploy.py -v` — 24 passed
- `chmod +x deploy.sh`
- `git commit` + `git push -u origin HEAD`

**Notes / follow-on work:**
- B-005 and B-006 were already fixed in a prior sprint — cli.py has `_db_exists()` checks and proper `json.dumps()` output. All 18 existing tests passed before any changes.
- The Playwright acceptance test ("after deploy, davidbmar.com shows search UI") requires a live deployment and is not runnable in CI without AWS credentials.


---

## agentB-index-export

*Completed: 2026-03-22 06:40 UTC*

### Files changed
- **`scripts/index-and-export.sh`** (new) — Executable pipeline script: sets up venv, runs `ghps index`, runs `ghps export`, prints summary
- **`web/data/repos.json`** (new) — 5 sample repos for development without GitHub token
- **`web/data/clusters.json`** (new) — 2 sample clusters matching export format
- **`docs/project-memory/sessions/S-2026-03-22-0639-sprint5-index-export.md`** (new) — Session doc

### Commands run
- `git fetch origin main && git merge origin/main` — synced with main
- `python3 -m pytest tests/test_export.py -v` — 24 passed
- `python3 -m pytest tests/ -v` — 123 passed, 1 warning
- `git push -u origin HEAD` — pushed branch

### Notes / follow-on work
- **export.py was already complete** — no fixes needed, all tests pass
- **.gitignore already had `.ghps/`** — no change needed
- The `index-and-export.sh` script requires `GITHUB_TOKEN` for real data; sample data in `web/data/` works without it
- The `github_client` module exposes `fetch_repos()` but the indexer's `index_user()` calls `github_client.fetch_user_repos()` — this mismatch is in agentA's domain (cli.py)


---

## agentC-web-access

*Completed: 2026-03-22 06:42 UTC*

### Files changed
- **`web/data/repos.json`** — new, 8 sample repositories
- **`web/data/clusters.json`** — new, 4 capability clusters
- **`web/js/app.js`** — fixed data fetch paths, added `#/clusters` and `#/access` routes, added `renderClustersPage()` and `renderAccessRequest()`
- **`web/index.html`** — added nav bar (Home | Search | Clusters | Request Access)
- **`web/css/style.css`** — added nav, access form, cluster description, and 375px responsive styles
- **`tests/test_web_playwright.py`** — new, 8 Playwright tests
- **`docs/project-memory/sessions/S-2026-03-22-0641-web-ui-improvements.md`** — session doc

### Commands run
- `git pull origin main`
- `pip install playwright` + `playwright install chromium`
- `python3 -m pytest tests/test_web_playwright.py -v` — **8/8 passed**
- `git commit` + `git push -u origin HEAD`

### Notes / follow-on work
- Access request form shows "Coming soon" message — needs backend `/api/access/request` endpoint
- Data files contain sample repos; agentB's export pipeline should replace these with real GitHub data

