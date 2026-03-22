agentA-deploy-fixes — Sprint 5

Sprint-Level Context

Goal
- Deploy the web UI to davidbmar.com (fix B-009)
- Fix remaining test failures (B-005, B-006)
- Add data export pipeline so the site has real content
- Begin gated access foundation (access request UI)

Constraints
- No two agents may modify the same files
- agentA owns deploy pipeline and bug fixes (deploy.sh, tests/test_cli.py, tests/test_e2e.py, src/ghps/cli.py)
- agentB owns data indexing and export (src/ghps/export.py, src/ghps/indexer.py, scripts/)
- agentC owns web UI improvements and access request page (web/)
- Use python3 for all commands
- Do NOT commit .venv/ or node_modules/ to git


Objective
- Fix test failures and create a working deploy script for davidbmar.com

Tasks
- Fix B-005: test_cli.py failures on missing index — add proper error handling in cli.py for when index DB doesn't exist
- Fix B-006: test_e2e.py JSON decode error — fix CLI --format json to output valid JSON
- Create deploy.sh in project root:
  - Check for web/ directory
  - If src/ghps/export.py exists, run ghps export --output web/data/
  - Run: aws s3 sync web/ s3://davidbmar-com/ --delete --exclude "*.pyc"
  - Run: aws cloudfront create-invalidation --distribution-id E3RCY6XA80ANRT --paths "/*"
  - Print: "Deployed to https://davidbmar.com"
- Make deploy.sh executable (chmod +x)
- Create tests/test_deploy.py — verify deploy.sh exists, is executable, has correct bucket name

Acceptance Criteria
- python3 -m pytest tests/test_cli.py tests/test_e2e.py -v passes with 0 failures
- ./deploy.sh runs without errors (when AWS credentials are available)
- Playwright test: after deploy, https://davidbmar.com shows search UI not placeholder
