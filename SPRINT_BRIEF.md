# Sprint 10

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

Merge Order
1. agentA-docs-cleanup
2. agentB-data-completeness
3. agentC-repo-detail

Merge Verification
- python3 -m pytest tests/ -v

## agentA-docs-cleanup

Objective
- Make all documentation accurate, current, and useful

Tasks
- Rewrite README.md:
  - Update architecture diagram to show current state (42+ repos, 6 clusters, live site)
  - Update Quick Start to include make commands (make install, make test, make deploy)
  - Update roadmap table with all 10 sprints
  - Add "Live Site" section with link to https://davidbmar.com
  - Add "Features" section listing: semantic search, faceted filtering, multi-word queries, capability clusters, relevance scoring, search highlighting, mobile responsive
  - Remove stale references to Sprint 2/3 being "next"
- Clean up docs/lifecycle/ROADMAP.md:
  - Remove stale "Phase 2/3/4" references in Next Up section
  - Ensure all completed sprints have (COMPLETED) dates
- Review and update CLAUDE.md if it exists
- Remove any stale TODO comments in documentation files

Acceptance Criteria
- README.md is accurate and a new contributor can get started in 5 minutes
- No references to sprints that haven't happened yet as "complete"
- Roadmap is internally consistent (no duplicate sprint numbers, no stale phases)

## agentB-data-completeness

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

## agentC-repo-detail

Objective
- Add a repo detail view so users can learn more about a specific repository

Tasks
- In web/js/app.js, add route handler for #/repo/<name>:
  - Show repo name as heading
  - Show full description
  - Show language, stars, last updated, topics
  - Show link to GitHub (html_url)
  - Show which cluster this repo belongs to
  - Show "Related repos" from same cluster (reuse existing component)
  - Add "Back to search" link
- Update web/js/search.js: make repo names in search results link to #/repo/<name> instead of directly to GitHub
- Update web/js/app.js: make repo names on home page link to #/repo/<name>
- Update web/css/style.css:
  - Style repo detail page (consistent with existing theme)
  - Make the GitHub link prominent with an icon or button style

Acceptance Criteria
- Playwright: click a repo name from search results → navigates to #/repo/<name>
- Playwright: repo detail page shows name, description, language, topics, GitHub link
- Playwright: "Related repos" section shows repos from same cluster
- Playwright: "Back to search" link works
- Mobile layout works at 375px
