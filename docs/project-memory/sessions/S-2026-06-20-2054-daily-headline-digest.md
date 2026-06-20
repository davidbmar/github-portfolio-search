# Session

Session-ID: S-2026-06-20-2054-daily-headline-digest
Title: Daily headline digest (/daily) via codex
Date: 2026-06-20
Author: David Mar (with Claude)

## Goal

A "build in public" daily digest: aggregate each day's commits across all of
davidbmar's repos, generate a headline + summary per day, publish a /daily feed.

## Context

Inspired by the generate_title_headline_hooks repo. Explored local MLX engines
(Qwen 9B cached; Gemma-4 12B won't load — multimodal "unified" type; downloaded
Gemma-3 12B but mlx_lm.server deadlocked under this machine's RAM pressure).
Pivoted to **codex** as the engine: `codex exec --sandbox read-only
--output-last-message` returns clean {headline,summary} JSON in ~5s, reliable.

## Decisions Made

- **Two-stage architecture:** a generate job writes web/data/daily.json; the web
  build just renders /daily. Same pattern as projects-search.json — keeps the LLM
  out of the fast static path.
- **Engine = codex (default), pluggable** to MLX (local Gemma-3 12B) or a
  deterministic no-LLM fallback, so /daily always renders.
- Scope: all davidbmar repo commits, aggregated by UTC day, backfill + ongoing.

## Changes Made

- `github_client.fetch_commits(owner, repo, since, until)` — paginated commits
  (sha, first-line message, author date); 404/409 → empty.
- `ghps/daily.py` — `aggregate_by_day`, `CodexEngine`/`MlxEngine`/
  `DeterministicEngine` + `resolve_engine`, `build_digests`, `write_daily`,
  `collect`.
- `render.render_daily_page(days)` — /daily feed (unified nav, newest-first cards
  with headline · date · summary · repo chips); empty-state.
- `generate.publish_all` renders /daily from daily.json when present.
- CLI `ghps daily --since --engine --owner --token`.
- Nav: "Daily" added to the SPA nav + unified static `_SITE_NAV`.
- Spec: docs/superpowers/specs/2026-06-20-daily-headline-digest-design.md

## Verified

- `ghps daily --since 2026-06-13 --engine codex`: 296 commits / 4 repos → 8 days.
  Headlines accurate + catchy (e.g. "AI-Readable Portfolio Docs Hit 132 Repos").
- /daily renders in browser: nav, 8 cards newest-first, chips, summaries.
- Full suite: 428 passed, 1 skipped (+12 new). Lint clean.

## Open Questions / Follow-ups

- Backfill all-history (this run was last-week window) — bounded codex cost.
- Ongoing: nightly CI runner can't run codex/MLX; run `ghps daily` locally on a
  schedule (or a cron with codex creds), commit daily.json.
- Not yet committed/deployed.

## Links

Commits: (pending)
PRs: (pending)
