agentA-data-pipeline — Sprint 6

Sprint-Level Context

Goal
- CRITICAL: Fix B-010 — davidbmar.com shows "Could not load data" because data files are empty
- Fix B-005, B-006 — remaining 4 test failures from Sprint 3
- Add sample data so the site works without a GitHub token
- Production hardening: proper error handling when data is missing

Constraints
- No two agents may modify the same files
- agentA owns data pipeline fixes (src/ghps/export.py, web/data/, scripts/)
- agentB owns test fixes and infrastructure (tests/, pyproject.toml, Makefile)
- agentC owns web UI error handling and resilience (web/js/app.js, web/js/search.js, web/index.html)
- Use python3 for all commands
- Do NOT commit .venv/ to git


Objective
- Create working sample data and fix the export pipeline so davidbmar.com has content

Tasks
- Create web/data/repos.json with realistic sample data: 10 repos representing David's portfolio (e.g., audio-stream-transcription, presigned-url-s3, grassyknoll, FSM-generic, tool-telegram-whatsapp, bot-customerobsessed, traceable-searchable-adr-memory-index, github-portfolio-search, tool-s3-cloudfront-push, everyone-ai). Each repo: name, description, language, topics array, stars, html_url, updated_at
- Create web/data/clusters.json with 4 capability clusters: "Voice & Audio Processing", "Infrastructure & DevOps", "AI & Search", "Web Applications"
- Verify src/ghps/export.py produces valid JSON matching this schema
- Create scripts/generate-sample-data.py that produces realistic sample data
- Update deploy.sh to check for valid data files before deploying

Acceptance Criteria
- web/data/repos.json is valid JSON with 10+ repos
- web/data/clusters.json is valid JSON with 4+ clusters
- Playwright: visit file:///path/to/web/index.html — search shows results, clusters render
