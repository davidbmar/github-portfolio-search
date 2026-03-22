# Roadmap & Architecture

## Roadmap

### Sprint Plan

**Sprint 1: Indexing Pipeline Foundation (COMPLETED 2026-03-22)**
Build goals: Set up GitHub API integration to fetch repo metadata, READMEs, and top-level source files for all ~90 repos. Implement the embedding generation step using sentence-transformers (server-side) or transformers.js (browser-native). Store embeddings and metadata in SQLite-vec. Produce a local vector store covering all repos.
PM/customer review checkpoint: Run Playwright tests simulating a developer querying the local index via CLI (`ghps search 'presigned URL pattern'`). Verify that results return and are ranked reasonably. Test that all ~90 repos are present in the index.
Backlog triage: Note any repos missing content, embedding quality issues, or slow indexing performance. Log GitHub API rate-limit edge cases.
Planning input for Sprint 2: Finalize depth-of-indexing decision (README only vs. README + top-level source files) based on quality of Sprint 1 results before building the REST API.

**Sprint 2: REST API and Core Search Endpoint (COMPLETED 2026-03-22)**
Build goals: Implement the Python REST API with core endpoints: `GET /api/search?q=<query>` (semantic search with ranked results), `GET /api/clusters` (capability clusters), and `GET /api/repos/<slug>` (repo detail). Wire the API to the SQLite-vec index from Sprint 1. Return structured JSON including repo name, description, tech stack tags, maturity badge, and matching snippets.
PM/customer review checkpoint: Use Playwright to simulate key use cases — semantic match ('upload files securely' should return presigned URL repos), capability cluster query ('auth' should return grouped Cognito/Auth0/SuperTokens/Cloudflare results), and dependency search ('transformers.js'). Verify <2s response time.
Backlog triage: Capture relevance tuning issues, missing metadata, and malformed API responses.
Planning input for Sprint 3: Confirm API contract is stable enough to build the Web UI and CLI against.

**Sprint 3: CLI and MCP Server (COMPLETED 2026-03-22)**
Build goals: Implement the `ghps` CLI tool supporting `search`, `clusters`, `repos`, and `reindex` commands. Implement the MCP server exposing `portfolio_search`, `portfolio_clusters`, `portfolio_repo_detail`, and `portfolio_reindex` tools. Both should call the REST API or read the local vector store directly. Test MCP integration with Claude Code.
PM/customer review checkpoint: Run Playwright/agent tests simulating Bob mid-conversation calling `portfolio_search('presigned URL')` and receiving structured JSON. Test CLI from terminal for all supported commands. Verify exclusion search ('voice NOT aws') works.
Backlog triage: Log MCP tool schema gaps, CLI UX friction, and any agent integration issues discovered.
Planning input for Sprint 4: Identify which UI components (capability tree, faceted search) are highest priority based on use-case coverage gaps.

**Sprint 4: Web UI — Public Tier and Browse Experience (COMPLETED 2026-03-22)**
Build goals: Build the static S3/CloudFront site. Implement the public tier: capability cluster browse (circle packing or treemap using React + D3.js), faceted search/filter panel with all defined facets (capability, tech stack, language, last active, maturity, has tests, has docs), and search results with result cards showing repo name, tags, description, and matching snippet. Implement mobile-responsive layout (vertical list on small screens, slide-out filter panel).
PM/customer review checkpoint: Use Playwright to simulate a recruiter visiting the public site with no auth — browse capability clusters, apply facet filters, search 'real-time voice processing', verify no code snippets appear in results. Test mobile viewport behavior.
Backlog triage: Capture visual design issues, facet count accuracy, dead-end facet values, and mobile layout bugs.
Planning input for Sprint 5: Define scope for gated tier and approval workflow.

**Sprint 5: Deploy Pipeline, Data Export, and Web UI Improvements (COMPLETED 2026-03-22)**
Build goals: Implement Google OAuth login flow. Build the access request form (note field, PENDING state). Integrate Telegram notifications via tool-telegram-whatsapp for approval alerts. Implement admin endpoints (`GET /api/access/pending`, `POST /api/access/approve/<id>`). Unlock code snippets, file tree browsing, and full-text semantic search for approved users. Build the activity timeline/heatmap view.
PM/customer review checkpoint: Use Playwright to simulate the full approval workflow — visitor requests access, David receives Telegram notification, approves, user gains gated access with code snippets visible. Test that unauthenticated users cannot see snippets. Verify heatmap renders correctly.
Backlog triage: Capture OAuth edge cases, Telegram integration failures, token/session management issues.
Roadmap extension checkpoint: Review remaining open questions (browser-native vs. server-side embeddings final decision, Afterburner dashboard integration, auto-refresh via GitHub webhooks, MCP Skill wrapper). Plan Sprints 7+ based on production feedback and priority.
Planning input for Sprint 6: Confirm auto-refresh and GitHub webhook integration is the next priority.

**Sprint 6: Stabilization — Fix Data Pipeline, Web Resilience, and Test Infrastructure (COMPLETED 2026-03-22)**
Build goals: Fix B-010 (empty data files — created sample repos.json with 10 repos and clusters.json with 4 clusters). Fix B-011 (playwright added to dev dependencies). Create Makefile with install/test/serve/index/export/deploy targets (F-003). Add web UI error handling — graceful fetch failures, sample data fallback, retry button, loading states. Add meta tags, OG tags, and favicon.
PM/customer review checkpoint: Deployed to davidbmar.com — search works (presigned URL returns correct repo with score 28.4), clusters render (4 categories), mobile layout works at 375px. 125 tests pass.
Backlog triage: B-010 fixed, B-011 fixed, F-003 fixed. B-005 and B-006 (4 test failures) still open — escalated to High.
Planning input for Sprint 7: Fix remaining 4 test failures (B-005, B-006), then move to real GitHub data indexing.

**Sprint 7: Test Fixes and Real Data Indexing (COMPLETED 2026-03-22)**
Build goals: Fixed B-005 (Click mix_stderr removed in 8.2+) and B-006 (progress bars corrupting JSON output). Indexed 42 real GitHub repos via API. Generated real repos.json (42 repos) and clusters.json (6 clusters). Deployed to davidbmar.com with real portfolio data. Tests: 129 passed, 0 failed, 1 skipped.
PM/customer review checkpoint: Full test suite passes. davidbmar.com live with real data — search for "presigned URL" returns S3-presignedURL repo (score 38.0). 6 clusters: Voice & Speech (11), Transcription & ASR (6), Browser-Native AI (6), AI & Search Tools (6), AWS Infra (6), Developer Tools (7). Faceted search works with real topics.
Backlog triage: B-005 fixed, B-006 fixed. B-012 (venv symlinks) still open. 42 of ~90 repos indexed (some may be private/empty).
Planning input for Sprint 8: Relevance tuning and UX polish — real data is live, now improve the experience.

**Sprint 8: Search Relevance and UX Polish (COMPLETED 2026-03-22)**
Build goals: Added title boosting (2x for name matches) and recency factor to search scoring. Added result highlighting (bold matched terms). Added "Related repos" section from same cluster. Added landing page stats (42 repos, 6 clusters, 5 languages), language bar chart, last updated timestamp. Improved card styling with hover effects and gradient accents. Added .env.example for GITHUB_TOKEN. Tests: 139 passed, 0 failed.
PM/customer review checkpoint: Live site shows polished UI with stats, search highlighting, and relevance bars. "voice" returns 9 repos with highlighted terms. "presigned URL" returns correct repo. Mobile works. New finding: multi-word queries like "voice processing" return 0 results — web search is keyword-exact, not fuzzy (F-005).
Backlog triage: B-012 still open. Added B-013 (keyword-only search) and F-005 (multi-word query support).
Planning input for Sprint 9: Fix multi-word search (F-005), then gated access.

**Sprint 9: Multi-Word Search Fix and Gated Access Prep (COMPLETED 2026-03-22)**
Build goals: Fixed F-005 (multi-word search — "voice processing" now returns 12 results via OR matching). Fixed B-012 (venv symlinks not created in worktrees). Added Request Access page with form (Name, Email, Reason). Added smoke tests. Cleaned up .gitkeep files. Tests: 141 passed, 0 failed.
PM/customer review checkpoint: "voice processing" returns 12 results. "s3 upload" returns S3 repos. Request Access page renders with 3 fields and Submit button. Mobile works. All tests pass.
Backlog triage: B-012 fixed, B-013 fixed, F-005 fixed. Only medium-priority items remain.
Planning input for Sprint 10: 5th-sprint checkpoint — extend roadmap, docs cleanup.

**Sprint 10: 5th-Sprint Checkpoint — Docs Cleanup and Repo Detail Page (COMPLETED 2026-03-22)**
Build goals: Rewrote README with Live Site section, Features list, updated architecture diagram, make commands. Added repo detail page (#/repo/name) with description, language, stars, topics, GitHub link, cluster context, and related repos. Validated data quality. Tests: 141 passed, 0 failed.
PM/customer review checkpoint: README is accurate. Repo detail page works — grassy-knoll shows description, Voice & Speech Processing cluster, 6 related repos. Related repos link to their own detail pages. "View on GitHub" button works.
Backlog triage: No new bugs. Extended roadmap to Sprint 15.
Planning input for Sprint 11: Activity visualization with D3.js.

**Sprint 11: Activity Visualization and Portfolio Analytics**
Build goals: Added D3.js circle-packing visualization on Clusters page. Added Recent Activity section (10 most recent repos). Added cluster stats summary (total repos, largest cluster, top language). Added search sort options. Added OG/Twitter meta tags. Also: indexed all 94 repos (up from 42) with .env token support, fixed cluster naming to be capability-based. Tests: 141 passed, 0 failed.
PM/customer review checkpoint: D3 viz renders with 6 named clusters. Recent Activity shows 10 repos sorted by date. Search sort works. 94 repos live. Cluster names are capability-oriented. Technology Distribution shows only 3 topics (most repos lack GitHub tags — B-014).
Backlog triage: Added B-014 (missing topics), B-015 (misclassified repos), F-006 (auto-tag from README).
Planning input for Sprint 12: Auto-tagging repos from README content would dramatically improve clusters and topic distribution.

**Sprint 12: Auto-Tagging and Cluster Quality (COMPLETED 2026-03-22)**
Build goals: Implemented F-006 (auto-infer topics from README content — 93/104 repos now have topics). Added topic extraction with word-boundary matching for 30+ technology keywords. Enriched cluster naming with inferred topics. Fixed B-014 (Technology Distribution now shows meaningful topics). Added password gate for site access. Indexed 104 repos including private repos. Tests: 152 passed, 0 failed.
PM/customer review checkpoint: Technology Distribution shows 15+ topics. Faceted search filters by aws (26), voice (22), browser (21), python (18), etc. Password gate works — "guild" grants session access. 104 repos live including private repos.
Backlog triage: B-014 fixed, B-015 fixed, F-006 fixed. Only medium/low items remain.
Planning input for Sprint 13: Gated access with OAuth is next priority.

**Sprint 13: Gated Access — Google OAuth and Approval Workflow (COMPLETED 2026-03-22)**
Build goals: Added Google OAuth frontend (web/js/auth.js) with GIS initialization, JWT decode, localStorage auth state, and password gate fallback when no clientId configured. Added FastAPI auth endpoints (POST /api/auth/verify, POST /api/access/request, GET /api/access/pending, POST /api/access/approve, POST /api/access/deny). Added Telegram notification module and CLI access management tool (scripts/approve-access.py). Tests: 192 passed, 0 failed, 1 skipped.
PM/customer review checkpoint: Request Access page renders with Name/Email/Reason form. Auth endpoints work (verify rejects invalid tokens, access request returns 200). Password gate fallback works when googleClientId is empty. Search returns 25 results for "voice processing". Mobile layout clean at 375px. Live site at davidbmar.com updated.
Backlog triage: B-017 fixed (google-auth not installed post-merge). Added F-007 (configure googleClientId), F-008 (Google Sign-In button activation). No critical bugs.
Planning input for Sprint 14: Need to configure Google Cloud OAuth client ID to activate Sign-In. Auto-refresh and webhooks are next priority per roadmap.

**Sprint 14: Auto-Refresh and Data Pipeline Improvements (COMPLETED 2026-03-22)**
Build goals: Created GitHub Actions workflow for automated reindex + deploy (`.github/workflows/reindex.yml`). Added `scripts/reindex.sh` standalone reindex script. Added freshness badges to web UI (green/blue/gray/red by recency). Added `indexed_at` timestamp to store, `--dry-run` flag to indexer, error resilience for failed repos. Fixed B-008/B-016 (API returns graceful error when no index exists). Tests: 212 passed, 0 failed, 1 skipped.
PM/customer review checkpoint: API returns `{"results":[],"error":"No index found..."}` with 200 instead of 500. Freshness badges render on repo cards. GitHub Actions YAML valid. Mixed content warning fixed (B-018). Google OAuth configured and live.
Backlog triage: B-008 fixed, B-016 fixed, B-018 fixed, F-007 fixed, F-008 fixed. Added B-019 (public tier blocked by OAuth gate) and F-009 (public browse without auth).
Planning input for Sprint 15: Public tier UX (B-019/F-009) is highest priority — the site should be browsable without sign-in.

**Sprint 15: 5th-Sprint Checkpoint — Public Tier UX and Polish (COMPLETED 2026-03-22)**
Build goals: Fixed B-019/F-009 (public tier now accessible without sign-in). Added "Sign In" button in nav bar. Added JSON-LD structured data (WebSite + Person schema). Updated meta tags to 104 repos. Created sitemap.xml and robots.txt. Added focus styles for keyboard nav and prefers-reduced-motion. Rewrote README with current features/architecture. Cleaned backlog (archived fixed items). Added Sprint 14 session doc. Tests: 212 passed, 0 failed, 1 skipped.
PM/customer review checkpoint: Visited davidbmar.com without sign-in — landing page shows 104 repos, 6 clusters, search works ("voice processing" → 25 results), mobile clean at 375px. "Sign In" button in top right. Freshness badges showing. SEO structured data deployed.
Backlog triage: B-019 fixed, F-009 fixed. Remaining: B-007 (Medium), F-002 (Low), F-004 (Medium). Roadmap extended to Sprint 20.
Planning input for Sprint 16: MCP integration is next — enable AI agents to search the portfolio.

**Sprint 16: MCP Integration and Agent Search**
Build goals: Expose portfolio search via MCP server for Claude Code and No Prob Bob. Add portfolio_search, portfolio_clusters, portfolio_repo_detail tools. Enable agents to search David's portfolio during conversations. Add search analytics (what people search for, popular repos).
PM/customer review checkpoint: Call portfolio_search("presigned URL") from Claude Code — verify structured JSON response. Test MCP tool discovery. Verify analytics capture search queries.
Backlog triage: MCP schema gaps, agent integration issues.
Planning input for Sprint 17: Based on agent usage patterns, tune search results.

**Sprint 17: Semantic Search Upgrade**
Build goals: Replace keyword-only web search with real semantic search (embeddings served via API or pre-computed similarity matrix). Add "related repos" powered by embeddings (not just same-cluster). Add search suggestions/autocomplete. Improve search result snippets with relevant README excerpts.
PM/customer review checkpoint: Search "how did I handle auth" → returns auth-related repos (semantic, not keyword). Related repos are genuinely similar. Autocomplete suggests popular queries.
Backlog triage: Search quality issues, false positive/negative results.
Planning input for Sprint 18: Based on search analytics, identify gaps.

**Sprint 18: Collaboration and Sharing**
Build goals: Shareable search result links (deep links with query + filters). Export search results as markdown/JSON. "Collections" — save groups of repos as named lists. Public portfolio embed widget (iframe-embeddable view for resume sites).
PM/customer review checkpoint: Share a search URL → recipient sees same results. Export works. Collections persist across sessions. Embed widget renders on external site.
Backlog triage: Sharing edge cases, embed security.
Planning input for Sprint 19: Based on collaboration usage, prioritize.

**Sprint 19: Analytics and Insights**
Build goals: Search analytics dashboard (popular queries, trending repos, visitor count). Repo activity heatmap (contribution calendar view). Technology trend analysis (which tech stacks are growing). Portfolio health score (test coverage, documentation, staleness).
PM/customer review checkpoint: Analytics dashboard shows real data. Heatmap renders accurately. Health scores match reality.
Backlog triage: Data accuracy, privacy concerns.
Planning input for Sprint 20: 5th-sprint checkpoint — plan Sprints 21-25.

**Sprint 20: 5th-Sprint Checkpoint — Browser-Native and Offline**
Build goals: Browser-native embeddings via transformers.js (search works offline). Service worker for offline access. PWA manifest for installability. Full end-to-end performance audit. Accessibility audit (WCAG 2.1 AA compliance). Plan Sprints 21-25.
PM/customer review checkpoint: Disconnect network → search still returns results from cached embeddings. Install as PWA on mobile. Lighthouse score >95. All WCAG AA issues resolved.
Roadmap extension checkpoint: Plan Sprints 21-25 based on production usage and feedback.
Planning input for Sprint 21: Based on offline usage and PWA installs, prioritize next phase.

### Current Focus

**Sprint 16: MCP Integration and Agent Search (Sprints 1-15 COMPLETE)**

Sprints 1-15 delivered: full stack portfolio search with 104 repos, D3.js visualization, faceted search, multi-word queries, search highlighting, relevance scoring, 6 capability clusters, Google OAuth + public tier, freshness badges, GitHub Actions reindex, SEO (structured data, sitemap), accessibility, and mobile support at davidbmar.com. 212 tests passing. Sprint 16 adds MCP tools so AI agents can search the portfolio.

### Next Up

**Sprint 17: Semantic Search Upgrade** — Real semantic search via embeddings, related repos, autocomplete, better snippets.

## Architecture

### System Overview

GitHub Portfolio Search indexes all repositories for a GitHub user into a vector store, enabling semantic search across READMEs and source files. Four interfaces share one index:

1. **REST API** (FastAPI) — foundation for web UI and external access
2. **CLI** (`ghps`) — local terminal search, calls REST or reads store directly
3. **MCP Server** — AI agent interface for Claude Code and No Prob Bob
4. **Web UI** (S3/CloudFront) — public portfolio + gated full access at davidbmar.com

```
GitHub API (repos, READMEs, source files)
       |
       v
  Indexing Pipeline (sentence-transformers + SQLite-vec)
       |
       +---> REST API (FastAPI)
       |       +-- Search, clusters, repo detail endpoints
       |       +-- Google OAuth + approval workflow
       |       +-- Telegram notifications (tool-telegram-whatsapp)
       |
       +---> CLI (ghps) -- local search
       +---> MCP Server -- Claude Code / Bob / any agent
       +---> Static Web UI (S3/CloudFront at davidbmar.com)
               +-- Public tier: browse clusters, search descriptions
               +-- Gated tier: full search + code snippets
```

### Key Decisions

1. **Server-side embeddings first** — sentence-transformers for indexing speed across 90 repos. Browser-native (transformers.js) deferred to Phase 6.
2. **SQLite-vec for vector storage** — lightweight, no infrastructure, already proven in developer's own repos (browser-RAG repos).
3. **FastAPI for REST** — async, fast, auto-generates OpenAPI docs.
4. **Static export for public site** — pre-built JSON data bundle deployed to S3. No server needed for public portfolio view.
5. **MCP over Skill** — MCP is the native tool interface for agents. Skill wrapper deferred unless opinionated prompt behavior is needed.
6. **D3.js circle-packing** for capability visualization — inspired by GitHub Next's repo visualization.
7. **Faceted navigation** inspired by Algolia/Sourcegraph patterns — filters alongside results, counts per facet, persistent filters.

### Technical Constraints

- IAM user `static-site-deployer` has S3 + CloudFront permissions but no Route53 — DNS must be configured separately
- ACM certificate required in us-east-1 for davidbmar.com
- GitHub API rate limits: 5000 req/hour authenticated — sufficient for 90 repos
- Embedding model size affects search quality vs. indexing speed tradeoff
- Private repos require GitHub token with repo scope

### Tech Stack

- **Backend:** Python 3.14, FastAPI, sentence-transformers, SQLite-vec
- **Frontend:** Vanilla JS, D3.js (circle-packing/treemap), CSS custom properties
- **Search:** Semantic similarity via embeddings + faceted filtering via metadata
- **Auth:** Google OAuth 2.0, JWT sessions
- **Infrastructure:** AWS S3, CloudFront, ACM (via tool-s3-cloudfront-push)
- **Notifications:** Telegram (via tool-telegram-whatsapp)
- **Agent interface:** MCP server (Python)
- **CLI:** Python click or argparse

