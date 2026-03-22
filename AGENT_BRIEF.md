agentA-topic-extraction — Sprint 12

Sprint-Level Context

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
