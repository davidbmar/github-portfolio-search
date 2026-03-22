agentB-cluster-quality — Sprint 12

Sprint-Level Context

Goal
- Auto-infer topics from README content so Technology Distribution and faceted search show meaningful data
- Fix misclassified repos in clusters
- Improve overall data quality

Constraints
- No two agents may modify the same files
- agentA owns topic extraction (src/ghps/indexer.py, src/ghps/github_client.py)
- agentB owns cluster quality and export (src/ghps/clusters.py, src/ghps/export.py)
- agentC owns web UI topic display (web/js/app.js, web/js/search.js, web/css/style.css)
- Use python3 for all commands
- Do NOT commit .venv/ to git
- .env contains GITHUB_TOKEN — code should auto-load it


Objective
- Improve cluster naming and fix misclassified repos

Tasks
- In src/ghps/clusters.py, update _generate_cluster_name to use inferred_topics from the database (not just GitHub topics):
  - Read topics from the repos table (which now includes inferred topics from agentA)
  - The _KEYWORD_CAPABILITIES mapping should match against these enriched topics
- In src/ghps/export.py, include inferred_topics in repos.json output:
  - Each repo should have a "topics" array that combines GitHub topics + inferred topics
  - This enables the web UI faceted search to filter by meaningful topics
- In src/ghps/clusters.py, reduce n_clusters to 6 (if not already) and add a minimum cluster size of 3 repos — if a cluster has fewer, merge it into the nearest neighbor
- Add a test: verify clusters have unique names (no duplicates)

Acceptance Criteria
- clusters.json has 6 clusters with unique, capability-oriented names
- repos.json has enriched topics for all repos
- No cluster has fewer than 3 repos
- python3 -m pytest tests/ -v passes
