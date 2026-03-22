agentA-data-export — Sprint 4

Sprint-Level Context

Goal
- Build the public web UI for davidbmar.com with search and browse capabilities
- Fix Sprint 3 test failures (B-005, B-006)
- Deploy static site to S3/CloudFront

Constraints
- No two agents may modify the same files
- agentA owns bug fixes and static data export (tests/, src/ghps/export.py)
- agentB owns web UI frontend (web/index.html, web/css/, web/js/)
- agentC owns deployment pipeline and integration (deploy.sh, web/api-proxy.js)
- Use python3 for all commands
- Frontend must be vanilla JS (no build step) — served as static files from S3
- Mobile-responsive layout required


Objective
- Fix test failures and build a static JSON data export for the web UI

Tasks
- Fix B-005: CLI test failures on missing index edge cases
- Fix B-006: JSON decode error in test_e2e.py
- Create src/ghps/export.py with:
  - export_static_bundle(store, output_dir) -> generates JSON files for static site
  - repos.json — all repos with metadata, description, language, topics, stars, url
  - clusters.json — capability clusters with repo names
  - search-index.json — pre-computed embeddings or search data for client-side search
- Add ghps export command to CLI: ghps export --db PATH --output web/data/
- Create tests/test_export.py

Acceptance Criteria
- python3 -m pytest tests/ -v passes with 0 failures
- ghps export produces valid JSON files in output directory
- repos.json contains all indexed repos with metadata
