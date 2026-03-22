agentC-repo-detail — Sprint 10

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
