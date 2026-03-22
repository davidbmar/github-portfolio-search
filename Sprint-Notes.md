# Sprint 15 — Agent Notes

*Started: 2026-03-22 20:37 UTC*

Phase 1 Agents: 3
- agentA-public-tier
- agentB-seo-perf
- agentC-docs-cleanup

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentB-seo-perf

*Completed: 2026-03-22 20:42 UTC*

```
This is the background task notification for the test run I already reviewed. The exit code 1 is from the 10 pre-existing Playwright test failures (port conflicts/missing browsers) — all 212 non-Playwright tests passed. I verified these same failures occur on `main` as well. No action needed; the work is already committed and pushed.
```


---

## agentC-docs-cleanup

*Completed: 2026-03-22 20:43 UTC*

## Files changed

| File | Action |
|------|--------|
| `README.md` | Updated Features (Google OAuth, freshness badges, 104 repos), Architecture (GitHub Actions), Tech Stack (google-auth, FastAPI) |
| `docs/project-memory/backlog/README.md` | Archived 18 fixed items into two historical tables, kept 5 open items |
| `docs/project-memory/sessions/S-2026-03-22-2039-sprint14-summary.md` | **New** — Sprint 14 session doc summarizing all 3 agents' work |
| `docs/seed/use-cases.md` | Added freshness check use case (I2) |
| `.gitignore` | Added sprint ephemera: `Sprint-Notes.md`, `.claude-output.txt`, `dashboard.json`, `ghps.db` |
| `.claude-output.txt`, `Sprint-Notes.md`, `dashboard.json`, `ghps.db` | Removed from git tracking (still on disk for sprint tooling) |

## Commands run

- `git pull origin main` — already up to date
- `make -n install/test/lint/export/deploy` — verified all make targets resolve
- `python3 -m pytest tests/ -v --ignore=tests/test_web_playwright.py` — **212 passed**, 0 failures
- `git push -u origin HEAD` — pushed to `agentC-docs-cleanup`

## Notes / follow-on work

- **Playwright tests** (`test_web_playwright.py`) have 9 pre-existing failures due to port conflicts — not related to this work. Tracked since Sprint 14.
- **B-019 / F-009** (public tier vs gated access separation) remain open — these are Sprint 15 agentA scope per the brief.
- **F-002** (progress bar for indexer) and **F-004** (auto-export before deploy) are low-priority open items that could be addressed in a future sprint.


---

## agentA-public-tier

*Completed: 2026-03-22 20:44 UTC*

### Files changed
| File | Change |
|---|---|
| `web/js/app.js` | Replaced 97-line auth gate IIFE with 15-line public-first init; rewrote `_updateHeaderUserInfo()` to show Sign In/avatar; added `_showSignInPopup()` modal; added sign-in section to Request Access page; removed `__ghpsGateLocked` check |
| `web/js/auth.js` | Added `isApproved()` stub (returns `true`); exported it in the module return |
| `tests/test_web_playwright.py` | Fixed `test_search_no_results` race condition — wait for search route DOM render instead of just hash change |
| `AGENT_BRIEF.md` | Already modified (pre-existing) |

### Commands run
- `git pull origin main` — already up to date
- `python3 -m pytest tests/ -v` — **222 passed**, 3 warnings
- `git push -u origin HEAD` — pushed to `agentA-public-tier`

### Notes / follow-on work
- **`Auth.isApproved()` is a stub** — returns `true` always. When a server-side access check is implemented, this should call the API to verify approval status.
- **No gated features currently exist** — the code checks `Auth.isAuthenticated()` in the access page and header, ready for future gated content gates using `Auth.isApproved()`.
- **Sign-out no longer reloads the page** — it just updates the header in-place since all content is public. This preserves scroll position and current route.

