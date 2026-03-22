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

**Sprint 9: Multi-Word Search Fix and Gated Access Prep**
Build goals: Fix F-005 (web search should split multi-word queries and match any term). Fix B-012 (venv symlinks). Add search result count to page title. Implement basic access request form (name, email, reason). Add "Request Access" page skeleton for gated tier. Clean up stale roadmap entries.
PM/customer review checkpoint: Search for "voice processing" should return voice repos. Search for "s3 upload" should return presigned URL repo. Request Access page shows form (no backend yet). All tests pass.
Backlog triage: Remaining UX friction, accessibility gaps.
Planning input for Sprint 10: 5th-sprint checkpoint — extend roadmap, full docs cleanup.

**Sprint 10: 5th-Sprint Checkpoint — Gated Access and Docs Cleanup**
Build goals: Implement access tiers (public: browse + search descriptions, gated: full code snippets). Add Google OAuth login flow. Build simple approval workflow (Telegram notification to David, approve/deny via link). Clean up all documentation — README, CLAUDE.md, API docs, deployment guide. Remove stale code and TODOs.
PM/customer review checkpoint: Test full approval workflow with Playwright — request access, receive notification, approve, verify gated content unlocks. Verify public tier shows no code snippets. Test that rejected users stay on public tier.
Backlog triage: OAuth edge cases, session management issues, notification reliability.
Roadmap extension checkpoint: Plan Sprints 12-16 based on usage patterns and feedback.
Planning input for Sprint 11: Prioritize based on real user feedback from gated access rollout.

**Sprint 11: Activity Visualization and Portfolio Analytics**
Build goals: Add D3.js capability tree (circle-packing visualization) showing the full portfolio at a glance. Build activity timeline/heatmap showing commit frequency across repos. Add portfolio analytics: most active repos, tech stack distribution, language breakdown. Create shareable portfolio link with OG tags for social media.
PM/customer review checkpoint: Visit davidbmar.com — verify capability tree renders and is interactive (click to zoom). Verify heatmap shows real activity data. Share the link on social media and verify OG preview renders correctly. Test on mobile.
Backlog triage: Visualization performance issues, data accuracy, mobile rendering bugs.
Planning input for Sprint 12: Based on user feedback and analytics, decide next priorities.

### Current Focus

**Sprint 9: Multi-Word Search Fix and Gated Access Prep (Sprints 1-8 COMPLETE)**

Sprints 1-8 delivered: full indexing pipeline, REST API, MCP server, CLI, web UI with faceted search, deploy pipeline, 42 real repos live on davidbmar.com, search highlighting, relevance scoring, language stats, and portfolio overview. Sprint 9 focuses on multi-word search support and gated access scaffolding.

### Next Up

**Sprint 10: 5th-Sprint Checkpoint** — roadmap extension, full docs cleanup, gated access with OAuth.

Finally **Phase 5: Public Deploy + Gated Access (Sprints 8-9)** — S3/CloudFront at davidbmar.com, Google OAuth, approval workflow with Telegram notifications, public/gated tiers.

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

