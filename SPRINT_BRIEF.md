# Sprint 15

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

Merge Order
1. agentA-public-tier
2. agentB-seo-perf
3. agentC-docs-cleanup

Merge Verification
- python3 -m pytest tests/ -v

## agentA-public-tier

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

## agentB-seo-perf

Objective
- Improve SEO, page performance, and web standards compliance

Tasks
- Update web/index.html:
  - Add structured data (JSON-LD) for WebSite and Person schema
  - Update meta description and OG tags to reflect 104 repos (currently says 42)
  - Add robots meta tag (index, follow)
  - Ensure all external scripts have integrity/crossorigin attributes where possible
- Create web/sitemap.xml:
  - Include main pages: /, /search, /clusters, /access
  - Add lastmod dates
- Update web/css/style.css:
  - Add prefers-reduced-motion media query for animations
  - Ensure focus styles are visible for keyboard navigation (WCAG 2.1 AA)
  - Optimize any large CSS selectors
- Add web/robots.txt with sitemap reference

Acceptance Criteria
- Structured data validates (test with Google Rich Results Test)
- Meta descriptions accurate (104 repos, not 42)
- sitemap.xml and robots.txt served correctly
- Focus styles visible on tab navigation
- Animations respect prefers-reduced-motion
- python3 -m pytest tests/ -v passes

## agentC-docs-cleanup

Objective
- 5th-sprint checkpoint docs cleanup and project memory maintenance

Tasks
- Update README.md:
  - Rewrite Features section to reflect current state (Google OAuth, 104 repos, freshness badges)
  - Update Architecture diagram to include GitHub Actions reindex
  - Update Tech Stack to include google-auth
  - Verify all make commands still work
- Review and update docs/project-memory/backlog/README.md:
  - Verify all Fixed items are actually fixed
  - Remove or archive items older than Sprint 10
  - Ensure priority assignments are accurate
- Add a session doc for Sprint 14 in docs/project-memory/sessions/
- Verify docs/seed/use-cases.md is still accurate — update if needed
- Clean up any stale files in the repo root (.agent-done-*, old logs)

Acceptance Criteria
- README.md accurately describes current features and architecture
- Backlog is clean and current
- Sprint 14 session doc exists
- No stale files in repo root
- python3 -m pytest tests/ -v passes
