agentC-infra-fixes — Sprint 8

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
- Fix venv symlink issue and improve developer experience

Tasks
- Fix B-012: Update .sprint/scripts/sprint-init.sh (or the local copy) to NOT symlink .venv into worktrees. Instead, each worktree should create its own venv or use the system python. Add a comment explaining why.
- Add .env.example file with GITHUB_TOKEN=ghp_xxx placeholder (for F-001)
- Update scripts/index-and-export.sh to source .env if it exists (python-dotenv style)
- Add a test that verifies ghps CLI --help works without a venv (basic smoke test)
- Update Makefile: add "reindex" target that runs the full index-and-export pipeline

Acceptance Criteria
- python3 -m pytest tests/ -v shows 0 failures, 0 errors
- make reindex works when GITHUB_TOKEN is set
- .env.example exists with clear instructions
- After sprint-init.sh creates worktrees, .venv is NOT symlinked (verify manually)
