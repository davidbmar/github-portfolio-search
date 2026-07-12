# Session

Session-ID: S-2026-07-12-1734-portfolio-constellation
Title: Portfolio Constellation — 3D star-map of the repo similarity graph
Date: 2026-07-12
Author: David Mar (with Claude)

## Goal

Render a constellation map of all public GitHub repos on davidbmar.com,
adapting the dependency-free canvas renderer from `~/src/missionmap`. Stars =
repos, constellations = semantic clusters, threads = embedding similarity.
First of two lenses over a shared "reuse graph"; the second (AI-facing MCP
tools) comes later.

## Context

`missionmap/constellation.js` reads one global `MISSION_DATA` and renders a 3D
star atlas with no dependencies. Our portfolio already exports the graph it
needs: `clusters.json` (6 named clusters), `similarity.json` (per-repo cosine
neighbors), `repos.json` (name/lang/stars/private), `projects.json` (title,
one_liner, reuse fields). Join is clean — repos.json names == cluster ids ==
similarity keys (104), all present as projects.json slugs.

## Plan

1. `scripts/export_constellation.py` — adapter: the 4 web/data JSONs → `web/data/constellation.json`.
2. Adapt missionmap renderer into `web/constellation.{html,css,js}` (fetch JSON,
   similarity edges not `connects`, drop the time-lapse, title labels, reuse panel).
3. Render locally for review.
4. Wire the exporter into `reindex.yml` after `ghps export`; deploy via workflow.

## Decisions Made

- **Edges = similarity only** (bright = top-2 neighbors, faint = the rest). Real
  repo→repo dependencies don't exist in the data (14 total; 892 deps are external
  tools). Clusters already carry the "what it's about" grouping.
- **Star size = score-weighted centrality** (own neighbor scores + how often
  others point to it). GitHub stars are dead (95/104 are 0); raw degree is
  saturated at 8.
- **Public repos only** — exclude 10 private repos from the public site → 94 stars.
- **Drop "Replay the Universe"** — no `created_at` in the data, only `updated_at`.
- **Labels = `title`** (slugs are up to 80 chars); status badge dropped (all "shipped").

## Open Questions

- Add `created_at` to indexing later to restore a birth-order time-lapse?
- Lens #2: MCP `similar_repos` / `starting_point` tools over the same graph.

## Links

Commits:
-

PRs:
-

ADRs:
-
