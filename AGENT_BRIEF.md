agentA-public-tier — Sprint 15

Sprint-Level Context

Goal
- Fix public tier: browse clusters, search descriptions, view repos WITHOUT sign-in
- Sign-in required only for gated features (code snippets, file trees, full semantic search)
- 5th-sprint checkpoint: SEO, performance, docs cleanup

Constraints
- No two agents may modify the same files
- agentA owns auth UX flow (web/js/app.js, web/js/auth.js)
- agentB owns SEO and performance (web/index.html, web/css/style.css, web/sitemap.xml — NEW FILE)
- agentC owns docs and cleanup (README.md, docs/lifecycle/ROADMAP.md, docs/project-memory/)
- Use python3 for all commands
- Do NOT commit .venv/ or .env to git
- The Google OAuth client ID is already configured — do not change web/config.json


Objective
- Make the site publicly browsable without sign-in (B-019, F-009)

Tasks
- Update web/js/app.js:
  - Remove the full-page auth gate overlay that blocks all content
  - Instead: load and display all public content (clusters, search, repo detail) WITHOUT requiring sign-in
  - Add a "Sign In" button in the nav bar (next to Request Access) that triggers Google Sign-In
  - After sign-in: show user avatar + name in header, show "Sign Out" button
  - Gated features (if any future gated content exists): check Auth.isAuthenticated() before showing
  - The Request Access page (#/access) should still show the sign-in flow for unauthenticated users
- Update web/js/auth.js:
  - Add isApproved() function stub (returns true for now — no server-side check on static site)
  - Ensure signOut() properly clears state and reloads without breaking public content

Acceptance Criteria
- Visit https://davidbmar.com without signing in → see landing page with 104 repos, clusters, search
- Search works without sign-in: "voice processing" returns results
- Mobile works without sign-in (375px viewport)
- "Sign In" button in nav bar triggers Google OAuth popup
- After sign-in: avatar + name in header, "Sign Out" works
- Request Access page shows sign-in for unauthenticated users
- python3 -m pytest tests/ -v passes
