agentC-mcp-tests — Sprint 16

Sprint-Level Context

Goal
- Expose portfolio search as MCP tools for Claude Code and AI agents
- Add search analytics (track queries, popular repos)
- Enable agents to search David's portfolio during conversations

Constraints
- No two agents may modify the same files
- agentA owns the MCP server (src/ghps/mcp_server.py — NEW FILE)
- agentB owns search analytics (src/ghps/analytics.py — NEW FILE, src/ghps/api.py)
- agentC owns MCP integration tests and CLI improvements (tests/test_mcp.py — NEW FILE, src/ghps/cli.py)
- Use python3 for all commands
- Do NOT commit .venv/ or .env to git
- The MCP server should use the existing search engine (src/ghps/search.py) and store (src/ghps/store.py)


Objective
- Test MCP tools and improve CLI with analytics integration

Tasks
- Create tests/test_mcp.py:
  - Test MCP tool registration (all 4 tools exist with correct schemas)
  - Test portfolio_search with mock store
  - Test portfolio_clusters with mock store
  - Test portfolio_repo_detail with mock store
  - Test error handling when no index exists
- Update src/ghps/cli.py:
  - Add `ghps stats` command — shows search analytics summary (total searches, top queries, avg results)
  - Log CLI searches to analytics (import from analytics.py)
- Add tests for the new CLI stats command

Acceptance Criteria
- tests/test_mcp.py covers all 4 MCP tools
- MCP tools handle edge cases (empty query, missing repo, no index)
- `ghps stats` shows analytics summary
- CLI searches are logged to analytics
- python3 -m pytest tests/ -v passes
