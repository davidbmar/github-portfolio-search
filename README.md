# GitHub Portfolio Search

Semantic search across 90+ GitHub repositories. Find patterns, architectures, and solutions from your own code — powered by embeddings.

## What It Does

Index all your GitHub repos by fetching READMEs and source files, generating embeddings with sentence-transformers, and storing them in SQLite-vec. Search semantically — ask "how did I handle auth?" instead of grepping for keywords.

## Architecture

```
GitHub API (repos, READMEs, source files)
       |
       v
  Indexing Pipeline (sentence-transformers + SQLite-vec)
       |
       +---> CLI (ghps search/index)
       +---> REST API (FastAPI) — Sprint 2
       +---> MCP Server — Sprint 3
       +---> Web UI (S3/CloudFront at davidbmar.com) — Sprint 4+
```

## Quick Start

```bash
# Set up
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Index your repos
export GITHUB_TOKEN=ghp_xxx
ghps index davidbmar

# Search
ghps search "presigned URL pattern"
ghps search "WebRTC streaming" --top-k 5
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
| 2 | REST API + core search endpoint | Planned |
| 3 | CLI improvements + MCP server | Planned |
| 4 | Web UI — public tier + browse | Planned |
| 5 | Gated access + approval workflow | Planned |
| 6 | Auto-refresh + production hardening | Planned |

## Deployment

Deploy the web UI to S3/CloudFront at davidbmar.com:

```bash
# Prerequisites: AWS CLI configured with appropriate credentials
# The script is idempotent — safe to run multiple times.

./deploy.sh
```

The deploy script will:
1. Run `ghps export` to generate fresh data (if available)
2. Copy web assets to a build directory
3. Upload to S3 (`davidbmar-com` bucket) via `aws s3 sync`
4. Invalidate the CloudFront cache (distribution `E3RCY6XA80ANRT`)
5. Print the live URL: https://davidbmar.com

Health check endpoint: `https://davidbmar.com/health.json`

## Tech Stack

- **Python 3.9+**, sentence-transformers, SQLite-vec, Click
- **Infrastructure:** AWS S3, CloudFront (davidbmar.com)
- **Framework:** [Afterburner](https://github.com/davidbmar/traceable-searchable-adr-memory-index) for sprint management

## License

Private — David Mar
