agentA-docs-cleanup — Sprint 10

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
