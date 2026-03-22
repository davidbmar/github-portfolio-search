agentA-oauth-frontend — Sprint 13

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
