agentA-test-fixes — Sprint 7

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
- Fix all 4 test failures to reach 0 failures, 0 errors

Tasks
- Fix B-005 (3 failures in test_cli.py): The `CliRunner(mix_stderr=False)` call fails because Click 8.2+ removed the `mix_stderr` parameter. Fix by removing `mix_stderr=False` from CliRunner() calls at lines 143, 283, 316 in tests/test_cli.py. Then ensure the tests actually test the missing-index edge case — cli.py should catch FileNotFoundError/TypeError when no SQLite DB exists and return a friendly error message via click.echo instead of crashing.
- Fix B-006 (1 failure in test_e2e.py): The `ghps search --format json` command outputs model loading progress bars (from sentence-transformers) to stdout, which corrupts the JSON. Fix by redirecting model loading output to stderr in src/ghps/cli.py — set environment variable or configure logging so that tqdm/transformers progress output goes to stderr. The JSON output on stdout must be clean (no progress bars, no warnings, just the JSON array). Alternatively, in the search command, capture stdout and extract only the JSON portion.
- Verify: python3 -m pytest tests/test_cli.py tests/test_e2e.py -v shows 0 failures

Acceptance Criteria
- python3 -m pytest tests/ -v shows 0 failures, 0 errors
- ghps search "test query" --format json outputs valid JSON to stdout (no progress bars mixed in)
- ghps search with no index returns a friendly error message, not a traceback
