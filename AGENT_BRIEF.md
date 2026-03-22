agentB-data-completeness — Sprint 10

Sprint-Level Context

Goal
- 5th-sprint checkpoint: clean up docs, index all ~90 repos, add repo detail page
- This is a quality/completeness sprint, not a feature sprint

Constraints
- No two agents may modify the same files
- agentA owns documentation cleanup (README.md, docs/)
- agentB owns data completeness (src/ghps/, web/data/, scripts/)
- agentC owns repo detail page (web/js/app.js, web/js/search.js, web/css/style.css)
- Use python3 for all commands
- Do NOT commit .venv/ to git


Objective
- Index as many repos as possible and ensure data quality

Tasks
- Review web/data/repos.json — check for repos with missing descriptions, null languages, or broken URLs
- Fix any repos with empty/null description: use repo name as fallback
- Fix any repos with null language: set to "Unknown"
- Ensure all html_url fields point to valid GitHub URLs (https://github.com/davidbmar/*)
- Update scripts/index-and-export.sh to validate output JSON after export
- If GITHUB_TOKEN is available: re-run indexing to capture any new repos since last index
- Update web/data/clusters.json: verify all repos are assigned to a cluster, no orphans

Acceptance Criteria
- web/data/repos.json has 0 repos with null/empty description
- web/data/repos.json has 0 repos with null language
- All html_url fields are valid GitHub URLs
- clusters.json accounts for all repos (sum of repo counts = total repos)
- python3 -c "import json; d=json.load(open('web/data/repos.json')); print(len(d))" shows 42+
