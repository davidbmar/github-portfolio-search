agentA-mcp-server — Sprint 16

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
- Create an MCP server that exposes portfolio search tools

Tasks
- Create src/ghps/mcp_server.py:
  - Use the MCP Python SDK (mcp package) to create a server
  - Expose these tools:
    - portfolio_search(query: str, limit: int = 10) → list of matching repos with name, description, score, language, topics
    - portfolio_clusters() → list of capability clusters with repo counts and names
    - portfolio_repo_detail(name: str) → full repo info including description, language, topics, stars, updated_at, html_url, cluster
    - portfolio_reindex() → trigger reindex (returns status message)
  - Each tool should read from the existing SQLite-vec store (src/ghps/store.py)
  - If no index exists, return helpful error message
  - Add proper tool descriptions and parameter schemas for discoverability
- Add mcp to pyproject.toml dependencies
- Create a standalone entry point: python3 -m ghps.mcp_server (for Claude Code config)
- Add __main__.py support so `python -m ghps.mcp_server` works

Acceptance Criteria
- MCP server starts without error: python3 -m ghps.mcp_server
- Tools are discoverable via MCP protocol
- portfolio_search("presigned URL") returns relevant repos
- portfolio_clusters() returns 6 clusters
- portfolio_repo_detail("github-portfolio-search") returns repo info
- When no index exists, tools return error message (not crash)
- python3 -m pytest tests/ -v passes
