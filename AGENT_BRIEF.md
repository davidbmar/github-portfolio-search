agentC-infra — Sprint 9

Sprint-Level Context

Goal
- CRITICAL: Fix F-005 — web search fails on multi-word queries ("voice processing" returns 0 results)
- Fix B-012 — .venv symlinks break after agent merges
- Add "Request Access" page skeleton for future gated tier
- Improve search result quality for recruiters

Constraints
- No two agents may modify the same files
- agentA owns web search fix (web/js/search.js, web/js/app.js)
- agentB owns access page and meta improvements (web/index.html, web/css/style.css)
- agentC owns infrastructure fixes (scripts/, .sprint/, Makefile, tests/)
- Use python3 for all commands
- Do NOT commit .venv/ to git


Objective
- Fix venv symlink issue and clean up infrastructure

Tasks
- Fix B-012: In .sprint/scripts/ (the local project copy), find where .venv gets symlinked into worktrees and remove that behavior. If sprint-init.sh or sprint-tmux.sh symlinks .venv, change it to skip .venv. Add a comment: "# .venv is NOT symlinked — each worktree uses system python or creates its own venv"
- Update Makefile: add "deploy" target that runs aws s3 sync + cloudfront invalidation
- Add a simple smoke test in tests/test_smoke.py: verify ghps --help returns 0, verify ghps search --help returns 0
- Clean up: remove any .gitkeep files from web/data/ (we have real data now)

Acceptance Criteria
- python3 -m pytest tests/ -v shows 0 failures, 0 errors
- make deploy works (syncs to S3 + invalidates CloudFront)
- .venv is NOT symlinked into worktrees after sprint-init.sh runs
- No .gitkeep files in web/data/
