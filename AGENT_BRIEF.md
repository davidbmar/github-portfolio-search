agentC-docs-cleanup — Sprint 15

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
