agentA-bug-fixes — Sprint 3

Sprint-Level Context

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
