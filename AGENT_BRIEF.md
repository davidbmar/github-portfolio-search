agentC-topic-ui — Sprint 12

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
- Display enriched topics in the web UI

Tasks
- In web/js/app.js:
  - Update the Technology Distribution section on Clusters page to show top 15 topics from repos.json topics arrays (not just GitHub topics)
  - Show topic count as horizontal bars
- In web/js/search.js:
  - Update faceted search to use enriched topics from repos.json
  - Show top 15 topics in the Topics filter panel (currently shows whatever is in repos.json)
  - Add topic counts next to each topic in the filter
- In web/css/style.css:
  - Style the Technology Distribution bars to match the cluster colors
  - Ensure topic filter panel doesn't overflow on mobile (scrollable if >10 topics)

Acceptance Criteria
- Playwright: Clusters page Technology Distribution shows 10+ meaningful topics with counts
- Playwright: Search faceted filter shows enriched topics
- Playwright: mobile viewport (375px) — topic filter is scrollable, no overflow
- No JS errors in console
