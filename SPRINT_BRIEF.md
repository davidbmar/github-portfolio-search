# Sprint 12

Goal
- Auto-infer topics from README content so Technology Distribution and faceted search show meaningful data
- Fix misclassified repos in clusters
- Improve overall data quality

Constraints
- No two agents may modify the same files
- agentA owns topic extraction (src/ghps/indexer.py, src/ghps/github_client.py)
- agentB owns cluster quality and export (src/ghps/clusters.py, src/ghps/export.py)
- agentC owns web UI topic display (web/js/app.js, web/js/search.js, web/css/style.css)
- Use python3 for all commands
- Do NOT commit .venv/ to git
- .env contains GITHUB_TOKEN — code should auto-load it

Merge Order
1. agentA-topic-extraction
2. agentB-cluster-quality
3. agentC-topic-ui

Merge Verification
- python3 -m pytest tests/ -v

## agentA-topic-extraction

Objective
- Auto-infer topics from README content during indexing

Tasks
- In src/ghps/indexer.py, after fetching README for each repo, extract topic keywords:
  - Scan README text for known technology keywords: voice, aws, s3, lambda, docker, react, python, typescript, llm, rag, whisper, webrtc, tts, stt, fastapi, flask, tensorflow, pytorch, kubernetes, terraform, cognito, cloudfront, sqs, dynamodb, api-gateway, websocket, grpc, mcp, telegram, whatsapp, fsm, state-machine, scheduler, browser, frontend, backend, cli, streaming, transcription, diarization, embeddings, vector, search, semantic
  - Also scan repo name (split on hyphens/underscores) for these keywords
  - Store inferred topics in the repo dict under "inferred_topics" key
  - Merge with any existing GitHub topics (deduplicate)
  - Store the merged topics in the database
- Update src/ghps/github_client.py fetch_repos(): ensure topics field from GitHub API is preserved (it already is, but verify pagination handles it)
- Add a test: given a repo with README containing "AWS Lambda S3", inferred topics should include ["aws", "lambda", "s3"]

Acceptance Criteria
- After indexing, repos have inferred_topics based on README content
- python3 -m pytest tests/ -v passes
- At least 80% of repos have 2+ inferred topics

## agentB-cluster-quality

Objective
- Improve cluster naming and fix misclassified repos

Tasks
- In src/ghps/clusters.py, update _generate_cluster_name to use inferred_topics from the database (not just GitHub topics):
  - Read topics from the repos table (which now includes inferred topics from agentA)
  - The _KEYWORD_CAPABILITIES mapping should match against these enriched topics
- In src/ghps/export.py, include inferred_topics in repos.json output:
  - Each repo should have a "topics" array that combines GitHub topics + inferred topics
  - This enables the web UI faceted search to filter by meaningful topics
- In src/ghps/clusters.py, reduce n_clusters to 6 (if not already) and add a minimum cluster size of 3 repos — if a cluster has fewer, merge it into the nearest neighbor
- Add a test: verify clusters have unique names (no duplicates)

Acceptance Criteria
- clusters.json has 6 clusters with unique, capability-oriented names
- repos.json has enriched topics for all repos
- No cluster has fewer than 3 repos
- python3 -m pytest tests/ -v passes

## agentC-topic-ui

Objective
- Display enriched topics in the web UI

Tasks
- In web/js/app.js:
  - Update the Technology Distribution section on Clusters page to show top 15 topics from repos.json topics arrays (not just GitHub topics)
  - Show topic count as horizontal bars
- In web/js/search.js:
  - Update faceted search to use enriched topics from repos.json
  - Show top 15 topics in the Topics filter panel (currently shows whatever is in repos.json)
  - Add topic counts next to each topic in the filter
- In web/css/style.css:
  - Style the Technology Distribution bars to match the cluster colors
  - Ensure topic filter panel doesn't overflow on mobile (scrollable if >10 topics)

Acceptance Criteria
- Playwright: Clusters page Technology Distribution shows 10+ meaningful topics with counts
- Playwright: Search faceted filter shows enriched topics
- Playwright: mobile viewport (375px) — topic filter is scrollable, no overflow
- No JS errors in console
