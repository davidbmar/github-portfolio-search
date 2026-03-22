agentB-analytics — Sprint 16

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
