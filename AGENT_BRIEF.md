agentB-auth-api — Sprint 13

Sprint-Level Context

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
