agentB-seo-perf — Sprint 15

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
