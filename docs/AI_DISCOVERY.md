# AI Discovery — how an agent finds and uses the project docs

The L0 generator publishes a corpus of AI-written, machine-readable docs for every
repo (one record per project). This page documents how an **AI agent** should
discover and consume that corpus **without saturating its context window** — the
spec's **L2 (AI discovery)** layer.

The design follows Anthropic's agent best practices: **progressive disclosure**.
Keep the always-loaded surface tiny; let the agent pull detail on demand instead of
loading all ~132 full records (or returning giant MCP payloads).

## The tiers

| Tier | Artifact | Size | When the agent reads it |
|------|----------|------|--------------------------|
| **0 — manifest** | [`/llms.txt`](https://davidbmar.com/llms.txt) | tiny | First. Tells the agent where everything is + how to query. |
| **1 — compact index** | [`/data/projects-index.json`](https://davidbmar.com/data/projects-index.json) | small | Scan all repos cheaply: `slug`, `title`, `one_liner`, `tech`, `reuse_tags`. Pick the few that matter. |
| **2 — full record** | `/projects/<slug>.record.json` | per-repo | Fetch **only** for the chosen slugs: full prose, Mermaid diagrams, `components`, `depends_on`, `integrates_with`, hygiene. |
| **— human page** | `/projects/<slug>.html` | per-repo | Rendered page (diagrams, screenshot, quickstart) for people. |
| **— full corpus** | `/data/projects.json` | large | Last resort — every record in one file. Avoid unless you truly need all of it. |

## Query interface (search, don't download)

For agentic use, prefer the MCP tool over downloading anything:

- **MCP server:** `ghps-mcp` (`ghps-mcp` console script / `python -m ghps.mcp_server`)
- **Tool:** `portfolio_find_docs(query)` → ranked matches `{slug, title, one_liner, score, matched}`
  searching the typed `capabilities`/`tech`/`patterns`/`reuse_tags`. Returns concise
  hits, not full records — the agent then fetches Tier-2 records for only the winners.
- Configure the feed it searches with `ghps-mcp --docs-feed web/data/projects.json`.

## Field semantics

- `reuse_tags`, `capabilities`, `patterns` — best signals for "have we built X / can I reuse Y?"
- `tech`, `depends_on`, `integrates_with` — stack and dependencies
- `thin: true` — fork / stub / empty repo; low signal, may be skipped

## Why not just one big JSON, or a fatter MCP response?

Loading `projects.json` (all records, with prose + two Mermaid diagrams each) into an
agent's context is expensive and crowds out the actual task. The compact index is
~10× smaller and is usually all an agent needs to decide *which* records to pull. The
MCP tool goes further — it does the selection server-side and returns only matches.
This mirrors how Anthropic's own tool-search and skills load detail on demand.

## How these artifacts are produced

`ghps gen-docs` writes one `projects/<slug>.record.json` per repo (LLM). Rendering is
decoupled: `ghps publish-docs` rebuilds **all** web artifacts (HTML pages, listing,
per-repo records, `projects.json`, `projects-index.json`, `llms.txt`) from those
records with **no LLM calls** — so a template change can be re-published cheaply.
`make deploy` syncs `web/` to S3/CloudFront.

## Optional: a Claude skill

`llms.txt` is universal — any AI that fetches the site discovers it. If you want a
Claude-specific shortcut, a small skill could wrap "query davidbmar.com/projects via
`portfolio_find_docs`, then fetch Tier-2 records" — but it would just encode what
`llms.txt` already advertises, so it's a convenience, not a requirement.
