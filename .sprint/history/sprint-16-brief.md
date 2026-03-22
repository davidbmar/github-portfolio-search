# Sprint 16

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

Merge Order
1. agentA-mcp-server
2. agentB-analytics
3. agentC-mcp-tests

Merge Verification
- python3 -m pytest tests/ -v

## agentA-mcp-server

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

## agentB-analytics

Objective
- Track search queries and popular repos for analytics

Tasks
- Create src/ghps/analytics.py:
  - Store search events in a SQLite table: query, timestamp, result_count, source (web/api/mcp/cli)
  - Functions: log_search(query, result_count, source), get_popular_queries(limit=20), get_search_stats()
  - get_search_stats() returns: total_searches, unique_queries, avg_results, top_queries, searches_today
  - Use ~/.ghps/analytics.db for storage (separate from main index)
- Update src/ghps/api.py:
  - Log searches in the /api/search endpoint via analytics.log_search()
  - Add GET /api/analytics/stats — returns search statistics (admin only, or public for now)
  - Add GET /api/analytics/queries — returns recent queries (last 100)
- Add tests for analytics logging, stats calculation, and API endpoints

Acceptance Criteria
- Search via API logs the query to analytics.db
- GET /api/analytics/stats returns valid JSON with search counts
- Analytics DB is separate from main index (~/.ghps/analytics.db)
- Analytics functions handle empty DB gracefully
- python3 -m pytest tests/ -v passes

## agentC-mcp-tests

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
