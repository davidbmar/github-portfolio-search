# GitHub Portfolio Search

Semantic search across 100+ GitHub repositories. Find patterns, architectures, and solutions from your own code — powered by embeddings.

## Live Site

**[davidbmar.com](https://davidbmar.com)** — browse capability clusters, search descriptions, and explore 104 indexed repos. No sign-in required.

## Features

- **TF-IDF + semantic search** — client-side search with inverted index, IDF weighting, and chunk text matching from README content
- **Multi-word queries** — "voice processing" returns 25+ relevant repos via OR matching with IDF boost
- **Faceted filtering** — filter by language, tech stack topics, and minimum stars
- **Capability clusters** — repos auto-grouped into 6 categories (Voice & Speech, Transcription & ASR, AI & Search, Media Processing, Browser & Frontend, etc.)
- **Embedding-powered related repos** — find similar projects via cosine similarity, not just cluster membership
- **Autocomplete** — search suggestions from repo names, topics, and popular queries
- **README snippets** — search results show relevant README excerpts with highlighted terms
- **Auto-generated descriptions** — repos without GitHub descriptions get one extracted from their README
- **"Secured" badges** — private repos clearly labeled as secured access only
- **Enhanced repo detail pages** — View on GitHub button, git clone command with copy button, full README content, clickable topic tags
- **Shareable URLs** — search results with filters persist in the URL for sharing
- **Collections** — save groups of repos as named lists (localStorage)
- **Export** — download search results as markdown or JSON
- **Embeddable widget** — `embed.html` for iframe embedding on resume sites
- **Google OAuth** — optional sign-in for gated features
- **Freshness badges** — repos show recency (today, this week, this month, stale)
- **MCP server** — AI agents (Claude Code, etc.) can search your portfolio via MCP tools
- **Automated reindexing** — GitHub Actions runs weekly to keep data fresh
- **Mobile responsive** — works on all screen sizes

## Getting Started

### Prerequisites

- Python 3.9+
- A GitHub Personal Access Token (for indexing private repos)
- AWS CLI configured (for deploying to S3/CloudFront)

### Install

```bash
git clone https://github.com/davidbmar/github-portfolio-search.git
cd github-portfolio-search

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Or use make:
make install
```

### Configure

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your GitHub token:
#   GITHUB_TOKEN=ghp_your_token_here
#
# Optional (for Google OAuth on the web UI):
#   GOOGLE_OAUTH_CLIENT_ID=your_client_id
#
# Optional (for Telegram notifications):
#   TELEGRAM_BOT_TOKEN=your_bot_token
#   TELEGRAM_CHAT_ID=your_chat_id
```

### Index Your Repos

```bash
# Index all repos for a GitHub user (includes private repos if token has repo scope)
ghps index davidbmar

# Check index status
ghps status
```

### Search

```bash
# Search from the CLI
ghps search "presigned URL"
ghps search "voice transcription"

# Start the API server
ghps serve --port 8000

# Export data for the web UI
ghps export
```

### Run the Web UI Locally

```bash
# Export fresh data first
ghps export

# Serve the web UI
cd web && python3 -m http.server 8000
# Open http://localhost:8000
```

### Deploy to Production

```bash
# Deploy to S3/CloudFront (davidbmar.com)
# This will: export data, validate, sync to S3, invalidate CloudFront cache
make deploy

# Or run directly:
./deploy.sh
```

The deploy script:
1. Runs `ghps export` to generate fresh JSON data files
2. Validates repos.json and clusters.json have content
3. Syncs `web/` to S3 (`davidbmar-com` bucket)
4. Invalidates the CloudFront cache
5. Site is live at https://davidbmar.com within ~60 seconds

### Run Tests

```bash
make test
# Or: python3 -m pytest tests/ -v
```

### Use with AI Agents (MCP)

Add to your `.mcp.json` or Claude Code config:

```json
{
  "mcpServers": {
    "portfolio": {
      "command": "/path/to/github-portfolio-search/.venv/bin/python",
      "args": ["-m", "ghps.mcp_server", "--db", "~/.ghps/index.db"],
      "cwd": "/path/to/github-portfolio-search"
    }
  }
}
```

Then from Claude Code:
- `portfolio_search("presigned URL")` — semantic search
- `portfolio_clusters()` — browse capability clusters
- `portfolio_repo_detail("voice-print")` — full repo info
- `portfolio_reindex()` — refresh the index

## Architecture

```
GitHub API (repos, READMEs, source files)
       |
       v
  Indexing Pipeline (sentence-transformers + SQLite-vec)
       |                        ^
       |                        |
       |              GitHub Actions (weekly cron)
       |
       +---> REST API (FastAPI)
       |       +-- Search, clusters, repo detail
       |       +-- Google OAuth + access control
       |
       +---> CLI (ghps) — terminal search + management
       +---> MCP Server — AI agent interface
       +---> Static Web UI (S3/CloudFront at davidbmar.com)
               +-- TF-IDF search with autocomplete
               +-- Embedding-powered related repos
               +-- Collections, export, shareable URLs
               +-- Embeddable widget (embed.html)
```

## Project Structure

```
src/ghps/
  github_client.py     # GitHub API client
  embeddings.py        # sentence-transformers pipeline
  store.py             # SQLite-vec vector store
  indexer.py           # Index orchestration
  search.py            # Semantic search engine
  clusters.py          # KMeans clustering
  export.py            # Static JSON export + auto-descriptions
  analytics.py         # Search event tracking
  cli.py               # Click CLI (ghps command)
  api.py               # FastAPI REST server
  mcp_server.py        # MCP server for AI agents
  auth.py              # Google OAuth + access lists
web/
  index.html           # SPA entry point
  embed.html           # Embeddable portfolio widget
  js/
    app.js             # Main app (routing, rendering)
    search.js          # Client-side TF-IDF search engine
    collections.js     # Collections manager (localStorage)
    export.js          # Markdown/JSON export
    d3-viz.js          # D3 circle-packing visualization
    auth.js            # Google OAuth
  css/style.css        # Styles with custom properties
  data/                # Generated JSON (repos, clusters, similarity, etc.)
tests/                 # 254 tests (pytest)
```

## Roadmap

| Sprint | Focus | Status |
|--------|-------|--------|
| 1-5 | Core pipeline, API, CLI, MCP, web UI, deploy | Complete |
| 6-10 | Stabilization, real data, relevance, UX, detail pages | Complete |
| 11-15 | D3 viz, auto-tagging, OAuth, GitHub Actions, public tier | Complete |
| 16 | MCP integration + search analytics | Complete |
| 17 | Semantic search upgrade (TF-IDF, similarity, autocomplete, snippets) | Complete |
| 18 | Collaboration (shareable URLs, collections, export, embed widget) | Complete |
| 19 | Analytics and insights dashboard | **Next** |
| 20 | Browser-native search (transformers.js) + PWA | Planned |

## Tech Stack

- **Python 3.9+**, sentence-transformers, SQLite-vec, Click, FastAPI
- **Frontend:** Vanilla JS, D3.js, CSS custom properties (no build step)
- **Search:** Server: embeddings + cosine similarity. Client: TF-IDF + inverted index
- **Auth:** Google OAuth 2.0, JWT sessions
- **Infrastructure:** AWS S3, CloudFront, GitHub Actions
- **AI Integration:** MCP server for Claude Code and other agents
- **Framework:** [Afterburner](https://github.com/davidbmar/traceable-searchable-adr-memory-index) for sprint management

## License

Private — David Mar
