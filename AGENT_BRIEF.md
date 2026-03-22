agentB-mcp-server — Sprint 3

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
