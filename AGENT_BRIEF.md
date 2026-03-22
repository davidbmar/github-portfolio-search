agentB-index-export — Sprint 5

Sprint-Level Context

Goal
- Deploy the web UI to davidbmar.com (fix B-009)
- Fix remaining test failures (B-005, B-006)
- Add data export pipeline so the site has real content
- Begin gated access foundation (access request UI)

Constraints
- No two agents may modify the same files
- agentA owns deploy pipeline and bug fixes (deploy.sh, tests/test_cli.py, tests/test_e2e.py, src/ghps/cli.py)
- agentB owns data indexing and export (src/ghps/export.py, src/ghps/indexer.py, scripts/)
- agentC owns web UI improvements and access request page (web/)
- Use python3 for all commands
- Do NOT commit .venv/ or node_modules/ to git


Objective
- Create a working index + export pipeline so the web UI has real data

Tasks
- Verify src/ghps/export.py works end-to-end:
  - export_static_bundle should produce repos.json, clusters.json in output dir
  - If export.py is broken or incomplete, fix it
- Create scripts/index-and-export.sh:
  - Set up venv if missing
  - Run ghps index davidbmar --db .ghps/index.db (requires GITHUB_TOKEN)
  - Run ghps export --db .ghps/index.db --output web/data/
  - Print summary: N repos indexed, M clusters generated
- Add sample/mock data to web/data/ for development:
  - web/data/repos.json with 5 sample repos (for testing without GitHub token)
  - web/data/clusters.json with 2 sample clusters
- Update .gitignore: add .ghps/ (index database)

Acceptance Criteria
- web/data/repos.json exists with valid JSON (sample or real data)
- web/data/clusters.json exists with valid JSON
- scripts/index-and-export.sh is executable and documents the pipeline
- ghps export --output web/data/ produces valid JSON files
