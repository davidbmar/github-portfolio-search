# Sprint 19

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

Merge Order
1. agentA-deploy-manifest
2. agentB-portfolio-indexer
3. agentC-portfolio-ui

Merge Verification
- python3 -m pytest tests/ -v

## agentA-deploy-manifest

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

## agentB-portfolio-indexer

Objective
- Read portfolio.json from each repo during indexing and export the data

Tasks
- Update src/ghps/github_client.py:
  - Add a function fetch_portfolio_json(owner: str, repo: str) -> dict | None:
    - Calls GitHub Contents API: GET /repos/{owner}/{repo}/contents/portfolio.json
    - If the file exists, decode the base64 content and parse as JSON
    - Return the parsed dict, or None if the file doesn't exist (404) or fails to parse
    - Handle errors gracefully (log warning, return None)
  - The function should use the same session/auth as other fetch functions

- Update src/ghps/store.py:
  - Add a "portfolio" TEXT column to the repos table CREATE TABLE statement
  - In add_repo(), accept and store repo_dict.get("portfolio", "") as JSON string
  - Update the INSERT statement to include the portfolio column

- Update src/ghps/indexer.py:
  - In index_repos() or index_user(), after fetching README for each repo:
    - Call github_client.fetch_portfolio_json(username, repo_name)
    - If portfolio data exists, add it to repo_meta as "portfolio": json.dumps(portfolio_data)
    - If not, set "portfolio": ""

- Update src/ghps/export.py:
  - In _build_repos(), read the portfolio column from the repos table
  - Parse the JSON string back to a dict
  - Add these fields to each repo in repos.json (only if portfolio data exists):
    - "showcase": bool (default false)
    - "liveUrl": string (default "")
    - "role": string (default "")
    - "builtWith": array of strings (default [])
    - "relatedProjects": array of {repo: string, relationship: string} (default [])
    - "highlight": string (default "")
    - "category": string (default "")
  - If no portfolio data, these fields are omitted or set to defaults
  - Update the SQL query to include the portfolio column (with try/except fallback for older DBs)

Acceptance Criteria
- fetch_portfolio_json returns parsed dict when portfolio.json exists in a repo
- fetch_portfolio_json returns None gracefully when file doesn't exist
- Indexing stores portfolio JSON in the repos table
- repos.json includes portfolio fields (showcase, liveUrl, role, builtWith, relatedProjects, highlight) for repos that have portfolio.json
- repos.json still works correctly for repos without portfolio.json (no extra fields or empty defaults)
- Indexing doesn't crash if portfolio.json is malformed
- python3 -m pytest tests/ -v passes

## agentC-portfolio-ui

Objective
- Show linked projects, showcase badges, and live demo buttons in the web UI

Tasks
- Update web/js/app.js:
  - In renderHome():
    - Before the "Capability Clusters" section, add a "Showcase" section
    - Filter repos where repo.showcase === true
    - Render showcase repos as larger featured cards with:
      - Repo name + "Featured" badge (gold/amber, like the "Secured" badge)
      - repo.highlight text as a tagline (if present)
      - repo.role as a subtitle (if present)
      - "Live Demo" button linking to repo.liveUrl (if present)
      - "View on GitHub" button
      - Language badge + star count
    - If no showcase repos exist, don't render the section at all
  - In renderRepoDetail():
    - If repo.liveUrl exists, add a "Live Demo" button next to "View on GitHub" in the actions area
      - Style: green background, opens in new tab
    - If repo.highlight exists, show it as a tagline/callout above the description
      - Style: slightly larger text, accent color
    - If repo.builtWith exists and has items, show a "Tech Stack" section
      - Render as a row of badges/pills
    - If repo.relatedProjects exists and has items, show a "Connected Projects" section BEFORE the "Related Repositories" (similarity-based) section
      - Each entry shows: linked repo name (clickable → #/repo/name) + relationship label
      - Example: "FSM-generic — powers the state machine engine"
    - If repo.showcase is true, show a "Featured" badge next to the repo name (like "Secured")
  - In renderRepoCards():
    - If repo.showcase is true, add a "Featured" badge next to the repo name
    - If repo.liveUrl exists, show a small "Demo" link/badge

- Update web/css/style.css:
  - Style .showcase-section: prominent section with distinct background
  - Style .showcase-card: larger card with gradient accent, more padding
  - Style .featured-badge: gold/amber pill badge (similar to .secured-badge but different color)
  - Style .live-demo-btn: green button for live demo links
  - Style .highlight-text: tagline/callout styling (larger, accent colored)
  - Style .tech-stack: row of small badges for builtWith items
  - Style .connected-projects: list of linked repos with relationship labels
  - Style .demo-badge: small badge for repo cards
  - Ensure mobile responsive for all new elements

Acceptance Criteria
- Showcase section appears on homepage when repos have showcase: true
- Showcase section is hidden when no repos have showcase: true
- Featured badge appears on showcase repo cards and detail pages
- Live Demo button appears on detail page when liveUrl is set
- Connected Projects section shows linked repos with relationship labels
- Tech Stack section shows builtWith items as badges
- Highlight text shows as tagline on detail page
- All elements are mobile responsive
- Graceful degradation: no errors if portfolio fields are missing
- python3 -m pytest tests/ -v passes
