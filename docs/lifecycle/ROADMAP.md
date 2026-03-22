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

**Sprint 3: CLI and MCP Server**
Build goals: Implement the `ghps` CLI tool supporting `search`, `clusters`, `repos`, and `reindex` commands. Implement the MCP server exposing `portfolio_search`, `portfolio_clusters`, `portfolio_repo_detail`, and `portfolio_reindex` tools. Both should call the REST API or read the local vector store directly. Test MCP integration with Claude Code.
PM/customer review checkpoint: Run Playwright/agent tests simulating Bob mid-conversation calling `portfolio_search('presigned URL')` and receiving structured JSON. Test CLI from terminal for all supported commands. Verify exclusion search ('voice NOT aws') works.
Backlog triage: Log MCP tool schema gaps, CLI UX friction, and any agent integration issues discovered.
Planning input for Sprint 4: Identify which UI components (capability tree, faceted search) are highest priority based on use-case coverage gaps.

**Sprint 4: Web UI — Public Tier and Browse Experience**
Build goals: Build the static S3/CloudFront site. Implement the public tier: capability cluster browse (circle packing or treemap using React + D3.js), faceted search/filter panel with all defined facets (capability, tech stack, language, last active, maturity, has tests, has docs), and search results with result cards showing repo name, tags, description, and matching snippet. Implement mobile-responsive layout (vertical list on small screens, slide-out filter panel).
PM/customer review checkpoint: Use Playwright to simulate a recruiter visiting the public site with no auth — browse capability clusters, apply facet filters, search 'real-time voice processing', verify no code snippets appear in results. Test mobile viewport behavior.
Backlog triage: Capture visual design issues, facet count accuracy, dead-end facet values, and mobile layout bugs.
Planning input for Sprint 5: Define scope for gated tier and approval workflow.

**Sprint 5: Gated Tier, Approval Workflow, and Roadmap Extension Checkpoint**
Build goals: Implement Google OAuth login flow. Build the access request form (note field, PENDING state). Integrate Telegram notifications via tool-telegram-whatsapp for approval alerts. Implement admin endpoints (`GET /api/access/pending`, `POST /api/access/approve/<id>`). Unlock code snippets, file tree browsing, and full-text semantic search for approved users. Build the activity timeline/heatmap view.
PM/customer review checkpoint: Use Playwright to simulate the full approval workflow — visitor requests access, David receives Telegram notification, approves, user gains gated access with code snippets visible. Test that unauthenticated users cannot see snippets. Verify heatmap renders correctly.
Backlog triage: Capture OAuth edge cases, Telegram integration failures, token/session management issues.
Roadmap extension checkpoint: Review remaining open questions (browser-native vs. server-side embeddings final decision, Afterburner dashboard integration, auto-refresh via GitHub webhooks, MCP Skill wrapper). Plan Sprints 7+ based on production feedback and priority.
Planning input for Sprint 6: Confirm auto-refresh and GitHub webhook integration is the next priority.

**Sprint 6: Auto-Refresh, Webhooks, and Production Hardening**
Build goals: Implement GitHub webhook listener to trigger re-indexing when repos are updated. Add periodic re-index fallback (cron). Deploy full stack to production (S3/CloudFront for static site, REST API on server). Build public and private data bundles (filtered vs. full). Add relevance indicators to result cards (semantic match score, freshness indicator, maturity badge, match source icon). Finalize private repo strategy — index with GitHub token, exclude from public bundle.
PM/customer review checkpoint: Use Playwright to push a commit to a test repo, verify the index updates and new content appears in search results within the expected window. Run all acceptance tests from the use-cases document (semantic match, temporal, recombination, maturity ranking, offline/browser, MCP tool call). Verify the full system end-to-end.
Backlog triage: Capture webhook reliability issues, stale index edge cases, deployment configuration bugs, and performance under full 90-repo load.
Planning input for Sprint 7+: Based on roadmap extension checkpoint from Sprint 5, prioritize from: Afterburner dashboard integration, MCP Skill wrapper, browser-native offline mode, advanced recombination search, and deeper source file indexing.

### Current Focus

**Phase 1: Index + Search Core (Sprints 1-2)**

Build the indexing pipeline that fetches all ~90 repos via GitHub API, generates embeddings with sentence-transformers, and stores them in SQLite-vec. Deliver a working CLI (`ghps search "query"`) that returns ranked results with code snippets in <2 seconds.

Key deliverables:
- GitHub API client: fetch repos, READMEs, top-level source files
- Embedding pipeline with sentence-transformers
- SQLite-vec vector store for persistence
- Basic CLI tool with semantic search
- Test: "presigned URL" returns S3-presignedURL repo; "voice" returns ~20 repos

### Next Up

**Phase 2: REST API + Faceted Search (Sprints 3-4)**

FastAPI server with search, clusters, and repo detail endpoints. Faceted filtering by capability, tech stack, language, last active date, and maturity level. Auto-generated capability clusters from embedding similarity.

Then **Phase 3: Web UI + Visualization (Sprints 5-6)** — search page with result cards, faceted sidebar, D3.js capability tree (circle-packing), activity timeline/heatmap, and browse-without-searching landing page.

Followed by **Phase 4: MCP + Agent Integration (Sprint 7)** — MCP server for Claude Code and Bob, private repo support.

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

