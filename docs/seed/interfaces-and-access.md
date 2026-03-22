# Interfaces and Access Model: GitHub Portfolio Search

## Interfaces

Four interfaces, one shared index:

### 1. REST API (Foundation)
Everything else calls this. Serves both the public site and authenticated users.

**Endpoints (draft):**
- `GET /api/search?q=<query>` — semantic search, returns ranked results
- `GET /api/clusters` — capability clusters (voice, auth, tools, etc.)
- `GET /api/repos/<slug>` — repo detail (README, file tree, metadata)
- `GET /api/repos/<slug>/snippets` — code snippets (gated, requires auth)
- `POST /api/access/request` — request access (Google OAuth)
- `GET /api/access/pending` — list pending requests (admin only)
- `POST /api/access/approve/<id>` — approve request (admin only)

### 2. CLI
For local use — quick searches from the terminal.

```bash
ghps search "presigned URL pattern"        # semantic search
ghps search "voice" --exclude aws          # exclusion search
ghps clusters                               # list capability groups
ghps repos --sort maturity                  # rank repos
ghps reindex                                # trigger re-indexing
```

Calls REST API or reads the local vector store directly (faster for local use).

### 3. MCP Server
The primary interface for AI agents (Claude Code, No Prob Bob, any MCP-compatible agent).

**Tools:**
- `portfolio_search(query, filters?)` — semantic search, returns structured JSON
- `portfolio_clusters()` — list capability clusters
- `portfolio_repo_detail(slug)` — full repo info with snippets
- `portfolio_reindex()` — trigger re-indexing

**Why MCP over Skill:** MCP is the tool interface — agents call it directly. A Skill is a prompt wrapper that calls tools. Since the MCP tool IS the interface, a Skill adds no new capability. Can add a Skill later if an opinionated prompt wrapper becomes useful (e.g., "search and suggest integration approach").

### 4. Web UI (S3/CloudFront)
Static site deployed to S3, served via CloudFront. Two tiers:

**Public tier (no auth):**
- Browse capability clusters
- Search repo names, descriptions, tech stacks
- View README summaries
- Link to GitHub repos

**Gated tier (Google OAuth + approval):**
- Full semantic search
- Code snippets in results
- File tree browsing
- Deeper README content

## Access Model

### Three Tiers

| Tier | Who | What they see | How it works |
|---|---|---|---|
| **Public** | Anyone | Repo names, descriptions, tech stacks, capability clusters, README summaries | Static S3 site, no server |
| **Approved** | Google OAuth + David's approval | Above + code snippets, file trees, full-text semantic search | Same site, richer data bundle behind auth |
| **Private** | David, Bob, Claude Code | Everything including private repos | Local MCP/CLI, or authenticated REST |

### Approval Workflow

1. Visitor lands on public portfolio site
2. Clicks "Request Full Access"
3. Signs in with Google OAuth
4. Writes a short note explaining why
5. Request goes to PENDING state
6. David gets notified via Telegram (tool-telegram-whatsapp integration)
7. David approves or denies (via Telegram reply, dashboard, or REST API)
8. Approved user gets a session/token for the gated tier
9. Access can be revoked anytime

### Private Repo Strategy
- All repos CAN be made private on GitHub
- The indexing pipeline uses a GitHub token with repo access
- Public site only includes repos explicitly marked for public display
- MCP/CLI always has full access (runs locally with the owner's credentials)

## Architecture

```
GitHub API (repos, READMEs, source files)
       |
       v
  Indexing Pipeline
  - Fetch repo metadata + content
  - Generate embeddings (sentence-transformers or transformers.js)
  - Store in vector DB (SQLite-vec)
  - Build public data bundle (filtered) + private data bundle (full)
       |
       +---> REST API (Python) ---> S3/CloudFront static site
       |       |                       +-- Public tier (filtered bundle)
       |       +-- Google OAuth         +-- Gated tier (full bundle, auth required)
       |       +-- Approval workflow
       |       +-- Telegram notifications
       |
       +---> CLI (ghps) -- calls REST or reads local store
       |
       +---> MCP Server -- Claude Code, Bob, any agent
```

## Integration Points

- **tool-telegram-whatsapp:** Approval notifications, possibly status alerts
- **No Prob Bob:** Calls MCP tools to search portfolio during conversations
- **Afterburner dashboard:** Project registered, sprint tracking, lifecycle docs
- **GitHub API:** Source of truth for repo data, webhooks for re-indexing
- **S3/CloudFront (tool-s3-cloudfront-push):** Deployment target for public site
