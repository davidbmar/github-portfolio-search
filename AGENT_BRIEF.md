agentC-deploy — Sprint 4

Sprint-Level Context

Goal
- Build the public web UI for davidbmar.com with search and browse capabilities
- Fix Sprint 3 test failures (B-005, B-006)
- Deploy static site to S3/CloudFront

Constraints
- No two agents may modify the same files
- agentA owns bug fixes and static data export (tests/, src/ghps/export.py)
- agentB owns web UI frontend (web/index.html, web/css/, web/js/)
- agentC owns deployment pipeline and integration (deploy.sh, web/api-proxy.js)
- Use python3 for all commands
- Frontend must be vanilla JS (no build step) — served as static files from S3
- Mobile-responsive layout required


Objective
- Build deployment pipeline to push web UI to S3/CloudFront at davidbmar.com

Tasks
- Create deploy.sh script that:
  - Runs ghps export to generate fresh data
  - Copies web/ files + data/ to a build directory
  - Uploads to S3 bucket davidbmar-com using aws s3 sync
  - Invalidates CloudFront cache (distribution E3RCY6XA80ANRT)
  - Prints the live URL
- Create web/data/.gitkeep (data dir for export output)
- Add deploy instructions to README.md
- Create a simple health check: web/health.json with version and last-deploy timestamp

Acceptance Criteria
- ./deploy.sh uploads files to S3 and invalidates CloudFront
- https://davidbmar.com shows the search UI after deploy
- deploy.sh is idempotent (safe to run multiple times)
