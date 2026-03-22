# Sprint 3

Goal
- Fix remaining packaging and test bugs from Sprint 1-2 (B-001, B-004)
- Build MCP server for Claude Code and Bob integration
- Improve CLI with better output formatting and error handling

Constraints
- No two agents may modify the same files
- agentA owns bug fixes and test reliability (pyproject.toml, tests/, Makefile)
- agentB owns MCP server (src/ghps/mcp_server.py, src/ghps/mcp_tools.py)
- agentC owns CLI improvements and end-to-end testing (src/ghps/cli.py, tests/test_cli.py, tests/test_e2e.py)
- Use python3 for all commands
- MCP server must follow the MCP protocol spec

Merge Order
1. agentA-bug-fixes
2. agentB-mcp-server
3. agentC-cli-e2e

Merge Verification
- python3 -m pytest tests/ -v

## agentA-bug-fixes

Objective
- Fix all test failures and packaging issues so the full test suite passes reliably

Tasks
- Fix B-001: editable install — ensure pip install -e ".[dev]" works and ghps is importable
- Fix B-004: test_embeddings.py and test_store.py collection errors — mock heavy dependencies (sentence-transformers, sqlite-vec) in unit tests so tests run without GPU/native deps
- Add conftest.py fixtures if not already present for mocking embeddings and store
- Create a Makefile with targets: install, test, lint, index, serve
- Add typing stubs or py.typed marker
- Ensure python3 -m pytest tests/ -v passes all tests with 0 failures

Acceptance Criteria
- pip install -e ".[dev]" succeeds on a clean venv
- python3 -m pytest tests/ -v passes with 0 errors, 0 failures
- make test runs the full suite
- make install sets up a working environment

## agentB-mcp-server

Objective
- Build an MCP server that exposes portfolio search tools for Claude Code and Bob

Tasks
- Add mcp dependency to pyproject.toml (or use the lightweight JSON-RPC approach)
- Create src/ghps/mcp_server.py with MCP server implementing these tools:
  - portfolio_search(query: str, top_k: int = 10) -> list of results with repo_name, score, snippet, url
  - portfolio_clusters() -> list of capability clusters with repo names
  - portfolio_repo_detail(repo_name: str) -> full repo metadata, README excerpt, tech stack
  - portfolio_reindex(username: str) -> trigger re-indexing, return count
- Each tool should have clear JSON Schema input/output descriptions
- Server should accept --db flag for index path (default: ~/.ghps/index.db)
- Add [project.scripts] entry: ghps-mcp = "ghps.mcp_server:main"
- Create tests/test_mcp.py with unit tests for each tool

Acceptance Criteria
- ghps-mcp starts without errors
- MCP tool list returns 4 tools with correct schemas
- portfolio_search returns ranked results
- portfolio_reindex triggers indexing

## agentC-cli-e2e

Objective
- Improve CLI output formatting and add end-to-end tests

Tasks
- Improve src/ghps/cli.py:
  - Add rich/click formatting for search results (colored scores, truncated snippets)
  - Add ghps serve command to start the FastAPI server
  - Add ghps status command showing index stats (repo count, chunk count, last indexed)
  - Add --format json flag for machine-readable output
  - Better error messages when index doesn't exist
- Create tests/test_cli.py with Click CliRunner tests:
  - Test ghps search with mock store
  - Test ghps index with mock GitHub API
  - Test ghps status with mock store
  - Test --format json output
- Create tests/test_e2e.py with end-to-end test:
  - Create temp index → index mock repos → search → verify results → clean up

Acceptance Criteria
- ghps search "query" shows colored, formatted results
- ghps serve starts the FastAPI server
- ghps status shows index statistics
- python3 -m pytest tests/test_cli.py tests/test_e2e.py -v passes
