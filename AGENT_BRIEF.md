agentA-search-relevance — Sprint 8

Sprint-Level Context

Goal
- Search relevance tuning — make semantic search return better results with real data
- UX polish — make the site look professional for recruiters and hiring managers
- Fix B-012 — .venv symlinks break after agent merges

Constraints
- No two agents may modify the same files
- agentA owns search relevance (src/ghps/search.py, src/ghps/embeddings.py, src/ghps/export.py)
- agentB owns web UI polish (web/js/app.js, web/js/search.js, web/css/style.css, web/index.html)
- agentC owns infrastructure fixes (tests/, scripts/, .sprint/, Makefile, pyproject.toml)
- Use python3 for all commands
- Do NOT commit .venv/ to git


Objective
- Improve search result quality with real data

Tasks
- In src/ghps/search.py, add title boosting: if query terms appear in repo name, boost score by 2x
- In src/ghps/search.py, add recency factor: repos updated in last 6 months get a 1.2x boost, last year 1.0x, older 0.8x
- In src/ghps/export.py, add "last_indexed" timestamp to repos.json metadata
- In src/ghps/export.py, sort repos by relevance score (stars + recency) not alphabetically
- Add a test in tests/test_search.py that verifies title boosting works (search for "presigned" should rank presigned-url repo first)
- Add a test that verifies recency boosting (recent repos ranked higher than stale ones, all else equal)

Acceptance Criteria
- python3 -m pytest tests/test_search.py -v passes with new relevance tests
- ghps search "presigned URL" returns S3-presignedURL repo as top result
- ghps search "voice" returns voice-related repos ranked by relevance
- repos.json includes last_indexed timestamp
