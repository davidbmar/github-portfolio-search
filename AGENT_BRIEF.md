agentB-real-data — Sprint 7

Sprint-Level Context

Goal
- Fix all 4 remaining test failures (B-005, B-006) to reach 0 failures
- Fix B-012 — .venv symlink breakage after agent merges
- Index real GitHub data (90+ repos) and deploy to davidbmar.com with real portfolio content

Constraints
- No two agents may modify the same files
- agentA owns test fixes (tests/test_cli.py, tests/test_e2e.py, src/ghps/cli.py)
- agentB owns indexing and data pipeline (src/ghps/embeddings.py, src/ghps/search.py, src/ghps/indexer.py, src/ghps/github_client.py, src/ghps/store.py, src/ghps/export.py, web/data/)
- Use python3 for all commands
- Do NOT commit .venv/ to git
- .sprint/scripts/sprint-init.sh must NOT symlink .venv into worktrees (B-012 fix)


Objective
- Index all of David's real GitHub repos and deploy real portfolio data

Tasks
- Create scripts/index-and-export.sh that:
  1. Checks for GITHUB_TOKEN env var (exit with helpful message if missing)
  2. Runs ghps index davidbmar to index all repos
  3. Runs ghps export to generate web/data/repos.json and web/data/clusters.json
  4. Validates the output JSON files are non-empty and valid
- Run the indexing pipeline: GITHUB_TOKEN must be available (check .env or environment)
- If GITHUB_TOKEN is not available, improve the sample data instead:
  - Ensure web/data/repos.json has accurate descriptions matching real repos
  - Add html_url links pointing to real GitHub URLs (https://github.com/davidbmar/*)
  - Ensure clusters.json groups repos logically
- Update src/ghps/export.py to handle edge cases:
  - Repos with no README should still appear (use description as fallback)
  - Repos with no language should show "Unknown"
  - Export should produce deterministic output (sorted by name)

Acceptance Criteria
- web/data/repos.json contains real repo data OR improved sample data with accurate GitHub URLs
- web/data/clusters.json has logical groupings
- scripts/index-and-export.sh exists and works end-to-end when GITHUB_TOKEN is set
- JSON files validate with python3 -c "import json; json.load(open('web/data/repos.json'))"
