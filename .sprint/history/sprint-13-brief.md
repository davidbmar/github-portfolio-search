# Sprint 13

Goal
- Replace password gate with Google OAuth for proper authentication
- Build access request → approval workflow with Telegram notifications
- Keep the site functional as a static S3/CloudFront deployment

Constraints
- No two agents may modify the same files
- agentA owns OAuth frontend (web/js/app.js, web/js/auth.js — NEW FILE)
- agentB owns backend API (src/ghps/api.py, src/ghps/auth.py — NEW FILE)
- agentC owns Telegram integration and admin (scripts/approve-access.py — NEW FILE, src/ghps/notifications.py — NEW FILE)
- Use python3 for all commands
- Do NOT commit .venv/ or .env to git
- The OAuth flow uses Google Identity Services (client-side only, no server redirect needed)

Merge Order
1. agentA-oauth-frontend
2. agentB-auth-api
3. agentC-telegram-admin

Merge Verification
- python3 -m pytest tests/ -v

## agentA-oauth-frontend

Objective
- Add Google Sign-In to replace the password gate

Tasks
- Create web/js/auth.js:
  - Initialize Google Identity Services (GIS) with client ID from config
  - Handle sign-in callback: decode JWT, extract email, name, picture
  - Store auth state in localStorage (token, email, name, expiry)
  - Export functions: isAuthenticated(), getUser(), signIn(), signOut()
  - If no Google client ID is configured, fall back to password gate ("guild")
- Update web/js/app.js:
  - Replace password gate with auth.js check: if isAuthenticated() → show app, else show sign-in page
  - Add user avatar/name in header when authenticated
  - Add "Sign Out" button in nav
  - Show "Request Access" for unauthenticated users who sign in but aren't approved
  - The Request Access page (#/access) should auto-fill name/email from Google profile
- Update web/index.html:
  - Add Google Identity Services script tag
  - Add meta tag for Google client ID (or load from config.json)
- Create web/config.json with placeholder: { "googleClientId": "", "apiUrl": "" }
  - When googleClientId is empty, use password gate fallback

Acceptance Criteria
- When googleClientId is empty: password gate still works (backward compatible)
- When googleClientId is set: Google Sign-In button appears
- After sign-in: user name and avatar show in header
- Sign Out clears auth state and shows sign-in page
- Request Access auto-fills from Google profile

## agentB-auth-api

Objective
- Add authentication endpoints to the FastAPI server

Tasks
- Create src/ghps/auth.py:
  - Verify Google JWT tokens (using google-auth library or manual JWT decode)
  - Maintain an access list in a JSON file (~/.ghps/access.json): list of approved emails
  - Functions: verify_token(token) → user_info, is_approved(email) → bool, approve_email(email), deny_email(email)
- Update src/ghps/api.py:
  - Add POST /api/auth/verify — accepts Google JWT, returns { approved: bool, user: {...} }
  - Add POST /api/access/request — accepts { email, name, reason }, stores in pending list, triggers notification
  - Add GET /api/access/pending — returns pending requests (admin only, check Authorization header)
  - Add POST /api/access/approve — accepts { email }, moves from pending to approved
  - Add POST /api/access/deny — accepts { email }, removes from pending
- Add google-auth to pyproject.toml dependencies
- Add tests: verify token validation, access list CRUD, request/approve flow

Acceptance Criteria
- POST /api/auth/verify with valid Google JWT returns user info + approval status
- POST /api/access/request stores request and returns 200
- Access list persists in ~/.ghps/access.json
- python3 -m pytest tests/ -v passes

## agentC-telegram-admin

Objective
- Send Telegram notifications when access is requested and provide approve/deny links

Tasks
- Create src/ghps/notifications.py:
  - Send Telegram message when access is requested: "🔔 Access Request: {name} ({email}) — {reason}"
  - Include approve/deny links in the message (pointing to API endpoints)
  - Use TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from .env
  - If Telegram credentials not set, log the request instead (graceful fallback)
- Create scripts/approve-access.py:
  - CLI tool: python3 scripts/approve-access.py approve user@example.com
  - CLI tool: python3 scripts/approve-access.py deny user@example.com
  - CLI tool: python3 scripts/approve-access.py list (show all pending + approved)
  - Reads/writes ~/.ghps/access.json
- Add tests for notification formatting and access list management

Acceptance Criteria
- When TELEGRAM_BOT_TOKEN is set: access request sends Telegram notification
- When not set: request is logged to console (no crash)
- scripts/approve-access.py list/approve/deny work correctly
- python3 -m pytest tests/ -v passes
