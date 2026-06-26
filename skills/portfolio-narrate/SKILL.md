---
name: portfolio-narrate
description: Scan recent merged PRs across the portfolio, cluster them into themes, and generate applied-tutorial Learn pages. Use when asked to "narrate the portfolio", "update the daily deep-dives", or "generate learn pages".
---

# Portfolio Narrate

Generate theme-grouped, code-grounded applied tutorials from merged PRs.

## Steps

1. Confirm you are in `~/src/github-portfolio-search` (or cd there):
   `cd ~/src/github-portfolio-search`
2. Ensure the venv + DashScope env are present:
   `test -d .venv && grep -q DASHSCOPE_API_KEY .env && echo ok`
3. Run the narrator over the repos of interest (default: all recently-pushed):
   `.venv/bin/ghps narrate --owner davidbmar --repos riff,github-portfolio-search --out web/learn --state web/data/narrate`
4. Report the printed summary (PRs processed, themes matured, pages written).
5. Preview a page locally: open `web/learn/index.html`.
6. To publish, deploy `web/` via the existing pipeline (`make deploy` or the gen-docs workflow). Do NOT hand-edit generated pages.

## Notes
- Records + ledger live in `web/data/narrate/`. Re-runs are idempotent (membership ledger); pass `--reclassify` only to deliberately re-cluster.
- v1 renders locally to `web/learn/`. Cross-repo `docs/html` publishing is a separate (v2) step — do not attempt it from this skill yet.
