# Plan

## Problem

Developers who build prolifically accumulate dozens or hundreds of GitHub repositories, each containing reusable patterns, solved problems, and proven architectures. But there's no way to search across them semantically — you can't ask "how did I handle WebRTC streaming?" or "what auth patterns do I have?" without manually remembering which repo has what. The result: developers rebuild solutions that already exist in their own portfolio, wasting time and losing institutional knowledge.

Today developers cope by: (1) manually searching GitHub repos one by one, (2) relying on memory for which repo has what, (3) rebuilding patterns they've already solved. This breaks down at ~30+ repos and fails completely at 90+.

## Appetite

6-week build (10 sprints), variable scope. The core (index + search + CLI) must ship in 2 sprints. Web UI and public portfolio are stretch goals. MCP integration is high priority because it provides daily value through Bob and Claude Code.

## Solution Sketch

Index all ~90 repos by fetching READMEs and top-level source files via GitHub API, generating embeddings with sentence-transformers, and storing in SQLite-vec. Serve search via four interfaces: REST API (FastAPI), CLI (`ghps`), MCP server (for AI agents), and a static web UI deployed to S3/CloudFront at davidbmar.com.

The web UI has two tiers: a public portfolio showcasing capability clusters (no code), and a gated tier (Google OAuth + manual approval) with full semantic search and code snippets. Browse without searching via a D3.js capability tree (circle-packing visualization). Filter via faceted navigation (capability, tech stack, language, activity date, maturity).

## Market Fit Analysis

Existing tools:
- **GitHub code search** — searches within repos, not across a user's portfolio semantically
- **Sourcegraph** — powerful but enterprise-focused, no portfolio/showcase mode
- **grep.app** — keyword search across GitHub, no semantic understanding
- **Personal portfolio sites** — static project lists, no search capability

**Gap:** No tool combines semantic search across a personal repo portfolio with visual browsing, faceted navigation, AI agent integration (MCP), and a public showcase mode. The closest is GitHub's own search, but it doesn't understand intent ("how did I handle auth?") or cluster by capability.

## Differentiation Strategy

1. **Semantic search, not keyword grep** — embeddings understand intent even when exact terms don't match
2. **Visual capability tree** — D3.js circle-packing shows the full portfolio at a glance, no query needed
3. **Faceted navigation** — filter by capability, tech stack, language, date, maturity
4. **MCP-native** — AI agents (Bob, Claude Code) can search the portfolio mid-conversation and suggest code reuse
5. **Portfolio showcase** — public site at davidbmar.com proves skills with searchable evidence, not bullet points
6. **Gated access** — Google OAuth + approval workflow lets you share the full library with trusted collaborators

## Rabbit Holes

- **Don't build browser-native first** — transformers.js + WASM is complex. Server-side sentence-transformers is faster and simpler for 90 repos. Browser-native is Phase 6.
- **Don't over-index** — start with READMEs + top-level source files. Full-repo deep indexing can come later.
- **Don't build custom auth** — use Google OAuth. Don't roll your own session management.
- **Don't optimize search relevance early** — get basic semantic search working first, tune with real queries later.
- **Don't build a complex approval dashboard** — start with Telegram notification + simple approve/deny reply.

## No-Gos

- No custom LLM inference — use embeddings for search, not a chat interface
- No multi-user write access — this is a personal portfolio tool, not a collaboration platform
- No real-time indexing — periodic re-index (daily cron or webhook) is sufficient
- No payment/monetization features
- No mobile app — responsive web only

## Sprint Candidates

**Sprint 1: Index + Search Foundation**
- GitHub API client to fetch all repos, READMEs, metadata
- Embedding pipeline with sentence-transformers
- SQLite-vec vector store
- Basic search function returning ranked results

**Sprint 2: CLI + Result Quality**
- CLI tool (`ghps search`, `ghps clusters`)
- README + top-level source file indexing
- Result ranking with relevance scores
- Capability cluster auto-generation

**Sprint 3: REST API + Facets**
- FastAPI server with search/clusters/detail endpoints
- Faceted filtering (capability, tech stack, language, date, maturity)
- Result cards with repo name, description, tags, activity
