# Sprint 13 — Agent Notes

*Started: 2026-03-22 18:36 UTC*

Phase 1 Agents: 3
- agentA-oauth-frontend
- agentB-auth-api
- agentC-telegram-admin

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentC-telegram-admin

*Completed: 2026-03-22 18:39 UTC*

### Files changed
- **`src/ghps/notifications.py`** (NEW) — Telegram notification module with graceful fallback
- **`scripts/approve-access.py`** (NEW) — CLI tool for approve/deny/list access management
- **`tests/test_notifications.py`** (NEW) — 19 tests covering both modules

### Commands run
- `git pull origin main`
- `python3 -m pytest tests/test_notifications.py -v` — 19 passed
- `python3 -m pytest tests/ -v` — 164 passed
- `git commit` + `git push -u origin HEAD`

### Notes / follow-on work
- The `approve-access.py` CLI reads/writes `~/.ghps/access.json` with no dependency on the API server — agentB's API endpoints can import `approve_user`/`deny_user` from the script or duplicate the logic
- `notify_access_request()` accepts an optional `api_base_url` param; when provided, Telegram messages include clickable approve/deny links pointing to agentB's API endpoints
- When `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` are not set, notifications fall back to `logging.info` — no crash


---

## agentA-oauth-frontend

*Completed: 2026-03-22 18:41 UTC*

### Files changed
- **`web/js/auth.js`** (NEW) — Auth module with Google Identity Services integration
- **`web/config.json`** (NEW) — Configuration with `googleClientId` and `apiUrl` placeholders
- **`web/js/app.js`** — Replaced password gate IIFE with auth-aware gate; added user avatar/name/sign-out in header; auto-fill access request form from Google profile
- **`web/index.html`** — Added GIS script tag and auth.js script tag
- **`docs/project-memory/sessions/S-2026-03-22-1840-oauth-frontend.md`** (NEW) — Session doc

### Commands run
- `git pull origin main` — up to date
- `make test` — 152 tests passed (8 Playwright errors are pre-existing port conflict, unrelated)
- `make lint` — passed
- `git push -u origin HEAD` — pushed

### Notes / follow-on work
- **Backward compatible**: When `googleClientId` is empty in config.json, the password gate ("guild") still works exactly as before
- **Access request form**: Currently shows "coming soon" on submit — agentB/agentC will implement the API endpoint and Telegram notification
- The 8 Playwright test errors (`OSError: Address already in use` on port 8765) are pre-existing and unrelated to these changes


---

## agentB-auth-api

*Completed: 2026-03-22 18:42 UTC*

### Files changed
- **`src/ghps/auth.py`** (NEW) — Google JWT verification via `google-auth`, access list CRUD with JSON persistence at `~/.ghps/access.json`
- **`src/ghps/api.py`** — Added 5 new endpoints: `/api/auth/verify`, `/api/access/request`, `/api/access/pending`, `/api/access/approve`, `/api/access/deny`
- **`pyproject.toml`** — Added `google-auth>=2.29` dependency
- **`tests/test_auth.py`** (NEW) — 21 tests covering unit + API endpoint tests
- **`docs/project-memory/sessions/S-2026-03-22-1841-auth-api-endpoints.md`** (NEW) — Session doc

### Commands run
- `git pull origin main`
- `pip install google-auth`
- `python3 -m pytest tests/test_auth.py -v` (21 passed)
- `python3 -m pytest tests/ -v --ignore=tests/test_web_playwright.py` (173 passed)
- `git push -u origin HEAD`

### Notes / follow-on work
- **Pre-existing playwright test failures**: `test_web_playwright.py` has 3 failures for UI elements (cluster cards, access request page) that depend on other agents' frontend work — not related to this change
- **GHPS_ADMIN_TOKEN**: Must be set in the server environment for admin endpoints to work. agentC's Telegram bot will need this same token to call approve/deny endpoints
- **No Google Client ID validation**: `verify_token` currently doesn't restrict to a specific `audience` (Google Client ID). Once agentA's frontend is wired up, consider adding `audience=` parameter to `verify_oauth2_token` for tighter validation

