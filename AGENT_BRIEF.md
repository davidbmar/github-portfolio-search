agentA-deploy-manifest — Sprint 19

Sprint-Level Context

Goal
- Deploy manifest: every deploy writes deploy-manifest.json to S3 with commit, timestamp, counts
- portfolio.json schema: per-repo config declaring relationships, live URLs, showcase status
- Indexer reads portfolio.json from each repo during indexing
- Web UI shows linked projects, showcase section, live demo buttons

Constraints
- No two agents may modify the same files
- agentA owns deploy tracking (deploy.sh)
- agentB owns the indexer pipeline (src/ghps/github_client.py, src/ghps/indexer.py, src/ghps/store.py, src/ghps/export.py)
- agentC owns the web UI (web/js/app.js, web/css/style.css)
- Use python3 for all commands
- Do NOT commit .venv/ or .env to git
- All web UI features must work in static mode (no API server required)
- portfolio.json is optional per repo — repos without it index normally


Objective
- Add deploy tracking so every deploy records what was deployed

Tasks
- Update deploy.sh:
  - After the data validation step and before the S3 sync, generate deploy metadata:
    - Get current git commit hash: git rev-parse --short HEAD
    - Get current branch: git rev-parse --abbrev-ref HEAD
    - Get current UTC timestamp
    - Count repos in repos.json: python3 -c "import json; print(len(json.load(open('web/data/repos.json'))))"
    - Count clusters in clusters.json similarly
    - Count files in web/ directory
  - Write web/deploy-manifest.json with this structure:
    ```json
    {
      "project": "github-portfolio-search",
      "commit": "16a046ce",
      "branch": "main",
      "deployedAt": "2026-03-23T16:12:29Z",
      "repoCount": 104,
      "clusterCount": 6,
      "fileCount": 14
    }
    ```
  - Update web/health.json with:
    ```json
    {
      "status": "ok",
      "commit": "16a046ce",
      "last_deploy": "2026-03-23T16:12:29Z",
      "repos": 104
    }
    ```
  - Both files are written BEFORE the S3 sync so they get uploaded with everything else
  - After the S3 sync and CloudFront invalidation, also append a line to a local deploy log file at .sprint/history/deploy-log.jsonl:
    - Same fields as deploy-manifest.json, one JSON line per deploy
    - Create the file if it doesn't exist
  - Print a summary after deploy: "Deployed commit XXXXX (104 repos, 6 clusters) to https://davidbmar.com"

Acceptance Criteria
- deploy.sh generates web/deploy-manifest.json before S3 sync
- deploy.sh updates web/health.json before S3 sync
- deploy.sh appends to .sprint/history/deploy-log.jsonl after deploy
- deploy-manifest.json has correct commit hash, timestamp, repo/cluster counts
- health.json has status, commit, last_deploy, repos fields
- Running deploy.sh twice produces two lines in deploy-log.jsonl
- python3 -m pytest tests/ -v passes
