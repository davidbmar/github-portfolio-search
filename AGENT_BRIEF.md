agentB-test-infra — Sprint 6

Sprint-Level Context

Goal
- CRITICAL: Fix B-010 — davidbmar.com shows "Could not load data" because data files are empty
- Fix B-005, B-006 — remaining 4 test failures from Sprint 3
- Add sample data so the site works without a GitHub token
- Production hardening: proper error handling when data is missing

Constraints
- No two agents may modify the same files
- agentA owns data pipeline fixes (src/ghps/export.py, web/data/, scripts/)
- agentB owns test fixes and infrastructure (tests/, pyproject.toml, Makefile)
- agentC owns web UI error handling and resilience (web/js/app.js, web/js/search.js, web/index.html)
- Use python3 for all commands
- Do NOT commit .venv/ to git


Objective
- Fix all remaining test failures and get to 0 failures / 0 errors

Tasks
- Fix B-005: test_cli.py TypeError on missing index — add try/except in cli.py for FileNotFoundError when DB doesn't exist, return helpful error message
- Fix B-006: test_e2e.py JSON decode error — ensure ghps search --format json outputs valid JSON even when no results found (output empty array, not error text)
- Add playwright to pyproject.toml [project.optional-dependencies] test group
- Create Makefile with targets: install, test, serve, index, export, deploy
- Remove or skip test_web_playwright.py tests if playwright browser not installed (use pytest.importorskip)

Acceptance Criteria
- python3 -m pytest tests/ -v shows 0 failures, 0 errors (playwright tests skipped if browser not installed)
- make test runs the full suite
- make install sets up the venv
- ghps search --format json returns valid JSON for empty results
