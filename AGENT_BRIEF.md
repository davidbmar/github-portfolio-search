agentC-telegram-admin — Sprint 13

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
