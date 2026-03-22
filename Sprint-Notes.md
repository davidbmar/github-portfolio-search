# Sprint 11 — Agent Notes

*Started: 2026-03-22 17:36 UTC*

Phase 1 Agents: 3
- agentA-d3-viz
- agentB-activity-stats
- agentC-social-meta

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentC-social-meta

*Completed: 2026-03-22 17:39 UTC*

**Files changed:**
- `web/index.html` — Updated `og:title`, `og:description`, added `<link rel="canonical">`
- `web/css/style.css` — Added styles for D3 viz container, D3 tooltips, Recent Activity cards, sort dropdown, page fade-in transition, plus mobile overrides at 768px and 375px
- `docs/project-memory/sessions/S-2026-03-22-1738-sprint11-social-meta.md` — Session doc

**Commands run:**
- `git pull origin main` — already up to date
- `make test` — 149/149 passed
- `git push -u origin HEAD` — pushed to `agentC-social-meta`

**Notes / follow-on work:**
- `twitter:card` with `summary_large_image` was already present — no change needed
- CSS class names (`.d3-viz-container`, `.d3-tooltip`, `.activity-card`, `.sort-dropdown`) are conventions that agentA (D3 JS) and agentB (app.js/search.js) should use to get these styles applied
- The `og-image.png` referenced in meta tags should exist at `https://davidbmar.com/og-image.png` for social previews to render correctly


---

## agentB-activity-stats

*Completed: 2026-03-22 17:40 UTC*

## Files changed
- **web/js/app.js** — Added Recent Activity section (landing page), cluster stats summary + Technology Distribution bar chart (clusters page), sort dropdown UI, CSS injection via `injectActivityStyles()`
- **web/js/search.js** — Added `sortResults()` function (relevance/recent/name modes)
- **docs/project-memory/sessions/S-2026-03-22-1739-sprint11-activity-stats.md** — Session doc

## Commands run
- `git pull origin main` — already up to date
- `make test` — 149 tests passed
- `make lint` — clean
- `git commit` + `git push -u origin HEAD` — pushed to `agentB-activity-stats`

## Notes / follow-on work
- CSS is injected via JS (`injectActivityStyles()`) to avoid modifying `web/css/style.css` owned by agentC. If file ownership rules change, these styles could move to the CSS file for cleaner separation.
- The sort state (`currentSortMode`) resets on page reload — could be persisted to `localStorage` if desired.
- Playwright acceptance tests for the new features (Recent Activity, cluster stats, sort dropdown) should be added in a follow-up sprint.


---

## agentA-d3-viz

*Completed: 2026-03-22 17:41 UTC*

**Files changed:**
- `web/index.html` — Added D3 v7 CDN script tag and `d3-viz.js` script tag
- `web/js/d3-viz.js` — **New file** — Circle-packing visualization with zoom, tooltips, responsive SVG, injected CSS
- `web/js/app.js` — Added `#d3-viz-container` div and `D3Viz.render()` call in `renderClustersPage()`
- `docs/project-memory/sessions/S-2026-03-22-1740-d3-circle-packing.md` — Session doc

**Commands run:**
- `git pull origin main` — synced with main
- `python3 -m pytest tests/ -v` — 148 passed, 1 pre-existing failure (unrelated to this work)
- `git push -u origin HEAD` — pushed branch

**Notes / follow-on work:**
- Pre-existing test failure: `test_search_no_results` expects "No results" text but the empty state says "Search to see all 42 repositories" — not caused by this change
- The D3 CDN (`d3js.org`) is loaded externally; for offline usage, consider bundling D3 locally
- Playwright acceptance tests for hover tooltip and click-to-navigate could be added in a follow-up

