agentC-cli-e2e — Sprint 3

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
