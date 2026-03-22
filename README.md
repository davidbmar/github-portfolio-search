# GitHub Portfolio Search

Semantic search across 100+ GitHub repositories. Find patterns, architectures, and solutions from your own code — powered by embeddings.

## Live Site

**[davidbmar.com](https://davidbmar.com)** — browse capability clusters, search descriptions, and explore 104 indexed repos with faceted filtering. No sign-in required for browsing and search.

## Features

- **Semantic search** — ask "how did I handle auth?" instead of grepping for keywords
- **Multi-word queries** — "voice processing" matches across terms via OR matching
- **Faceted filtering** — filter by capability, tech stack, language, maturity, and more
- **Capability clusters** — repos grouped into 6 categories (Voice & Speech, Transcription & ASR, Browser-Native AI, AI & Search Tools, AWS Infra, Developer Tools)
- **Relevance scoring** — title boosting (2x for name matches) and recency factor
- **Search highlighting** — matched terms bolded in results
- **Mobile responsive** — vertical list layout with slide-out filter panel on small screens
- **Google OAuth** — sign in with Google to request access to gated features (code snippets, file trees, full semantic search)
- **Freshness badges** — each repo shows how recently it was indexed (today, this week, this month, stale)
- **Automated reindexing** — GitHub Actions workflow runs weekly + manual dispatch to keep data fresh

## Architecture

```
GitHub API (repos, READMEs, source files)
       |
       v
  Indexing Pipeline (sentence-transformers + SQLite-vec)
       |                        ^
       |                        |
       |              GitHub Actions (weekly cron + manual dispatch)
       |
       +---> REST API (FastAPI)
       |       +-- Search, clusters, repo detail endpoints
       |       +-- Google OAuth verification
       |
       +---> CLI (ghps) — local terminal search
       +---> MCP Server — AI agent interface
       +---> Static Web UI (S3/CloudFront at davidbmar.com)
               +-- Browse clusters, search, faceted filtering (public)
               +-- Google Sign-In + Request Access (gated features)
               +-- Freshness badges per repo
```

## Quick Start

```bash
# Install
make install
# — or manually:
# python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

# Run tests
make test

# Index your repos
export GITHUB_TOKEN=ghp_xxx
make index USER=davidbmar

# Export data for web UI
make export

# Deploy to S3/CloudFront
make deploy
```

## Project Structure

```
src/ghps/
  __init__.py          # Package version
  github_client.py     # GitHub API client (repos, READMEs, source files)
  embeddings.py        # sentence-transformers embedding pipeline
  store.py             # SQLite-vec vector store
  indexer.py           # Ties client + embeddings + store together
  search.py            # Semantic search engine
  cli.py               # Click-based CLI
tests/                 # Unit tests
docs/
  lifecycle/           # Vision, Plan, Roadmap
  seed/                # Source materials for lifecycle doc generation
  project-memory/      # Sessions, ADRs, backlog
```

## Roadmap

| Sprint | Focus | Status |
|--------|-------|--------|
| 1 | Indexing pipeline + search + CLI | Complete |
| 2 | REST API + core search endpoint | Complete |
| 3 | CLI improvements + MCP server | Complete |
| 4 | Web UI — public tier + browse | Complete |
| 5 | Deploy pipeline + data export | Complete |
| 6 | Stabilization — sample data + web resilience | Complete |
| 7 | Test fixes + real data indexing (42 repos) | Complete |
| 8 | Search relevance + UX polish | Complete |
| 9 | Multi-word search + gated access prep | Complete |
| 10 | Docs cleanup + repo detail page | Complete |
| 11 | Activity visualization + D3.js + 94 repos | Complete |
| 12 | Auto-tagging + cluster quality + password gate | Complete |
| 13 | Gated access — Google OAuth + approval | Complete |
| 14 | Auto-refresh + GitHub Actions + freshness badges | Complete |
| 15 | 5th-sprint checkpoint — public tier UX + polish | Complete |
| 16 | MCP integration + agent search | **Next** |
| 17 | Semantic search upgrade | Planned |
| 18 | Collaboration and sharing | Planned |
| 19 | Analytics and insights | Planned |
| 20 | Browser-native + offline + PWA | Planned |

## Deployment

Deploy the web UI to S3/CloudFront at davidbmar.com:

```bash
# Prerequisites: AWS CLI configured with appropriate credentials
# The script is idempotent — safe to run multiple times.

make deploy
# — or: ./deploy.sh
```

The deploy script will:
1. Run `ghps export` to generate fresh data (if available)
2. Copy web assets to a build directory
3. Upload to S3 (`davidbmar-com` bucket) via `aws s3 sync`
4. Invalidate the CloudFront cache (distribution `E3RCY6XA80ANRT`)
5. Print the live URL: https://davidbmar.com

Health check endpoint: `https://davidbmar.com/health.json`

## Tech Stack

- **Python 3.9+**, sentence-transformers, SQLite-vec, Click, FastAPI
- **Auth:** google-auth for OAuth token verification
- **Infrastructure:** AWS S3, CloudFront (davidbmar.com), GitHub Actions (reindex workflow)
- **Framework:** [Afterburner](https://github.com/davidbmar/traceable-searchable-adr-memory-index) for sprint management

## License

Private — David Mar
