# Sprint 6 — Agent Notes

*Started: 2026-03-22 07:08 UTC*

Phase 1 Agents: 3
- agentA-data-pipeline
- agentB-test-infra
- agentC-web-resilience

Phase 2 Agents: 0
(none)

Automated summaries from each agent are appended below as they complete.

---

## agentA-data-pipeline

*Completed: 2026-03-22 07:12 UTC*

## Files changed
- **web/data/repos.json** — Replaced 5 generic repos with 10 realistic portfolio repos
- **web/data/clusters.json** — Replaced 2 generic clusters with 4 capability clusters
- **scripts/generate-sample-data.py** — New: reproducible sample data generator with validation
- **deploy.sh** — Added `validate_json()` gate before S3 sync
- **docs/project-memory/sessions/S-2026-03-22-0711-sprint6-data-pipeline.md** — Session doc

## Commands run
- `git fetch origin main && git merge origin/main` — sync with main
- `python3 scripts/generate-sample-data.py` — verified generator works
- `python3 -m pytest tests/ -v` — **137 passed**, 1 warning
- `git push -u origin HEAD` — pushed to remote

## Notes / follow-on work
- The brief requested `html_url` but the existing app.js and export.py use `url`. Both fields are included in sample data for compatibility. If `export.py` is updated to emit `html_url`, the web UI (`app.js:428`) would also need updating (agentC's domain).
- The `validate_json()` function in deploy.sh uses `python3` for JSON parsing — this is already a project dependency so no new deps added.
- The sample data generator can be re-run anytime with `python3 scripts/generate-sample-data.py` to reset data files to known-good state.


---

## agentB-test-infra

*Completed: 2026-03-22 07:13 UTC*

### Files changed
- **`pyproject.toml`** — Added `test` optional-dependency group with `playwright>=1.40`
- **`tests/test_web_playwright.py`** — Added `pytest.importorskip("playwright")` at module level for graceful skip
- **`Makefile`** — Added `export` and `deploy` targets, updated `.PHONY` list
- **`docs/project-memory/sessions/S-2026-03-22-0711-sprint6-test-infra.md`** — Session doc

### Commands run
- `git pull origin main` — ensured up to date
- `python3 -m pytest tests/ -v` — 137 passed, 0 failures, 0 errors
- `make test` — confirmed it runs the full suite successfully
- `git push -u origin HEAD` — pushed to remote

### Notes / follow-on work
- **B-005 and B-006 were already fixed** in `cli.py` from prior sprints. The `_db_exists()` guard handles missing DB (B-005), and the JSON format branch outputs valid JSON even for empty results (B-006).
- Playwright tests pass on this machine (browser installed). On systems without playwright, all 8 tests will show as **skipped** rather than erroring.
- The `deploy` target depends on `scripts/deploy.sh` existing — it validates before running.


---

## agentC-web-resilience

*Completed: 2026-03-22 07:13 UTC*

### Files changed
- `web/js/app.js` — Error handling with retry button, sample data fallback, loading skeleton, footer
- `web/js/search.js` — Guard clauses for empty/null repos in `search()`, `applyFilters()`, `extractFacets()`
- `web/css/style.css` — Loading skeleton animation, error banner styles, retry button, footer, sticky footer layout, mobile responsive
- `web/index.html` — Meta description, OG tags, Twitter card, SVG emoji favicon
- `docs/project-memory/sessions/S-2026-03-22-0712-sprint6-web-resilience.md` — Session doc

### Commands run
- `git pull origin main` — merged latest
- `python3 -m pytest tests/ -v` — 137 passed
- `node -e ...` — verified search.js handles empty/null data
- `git push -u origin HEAD` — pushed to remote

### Notes / follow-on work
- **Playwright tests** mentioned in acceptance criteria (visit site with empty data, sample data, mobile 375px viewport) are not yet implemented — these would be added by the test agent (agentB) per the constraint boundaries
- The sample fallback data is minimal (1 repo, 1 cluster) — could be enriched with more representative examples

