# Sprint 2

Goal
- Fix Sprint 1 packaging bugs so tests pass and CLI works
- Build the REST API with search, clusters, and repo detail endpoints
- Wire API to the SQLite-vec index from Sprint 1

Constraints
- No two agents may modify the same files
- agentA owns packaging fixes and test fixes (pyproject.toml, tests/, .github/)
- agentB owns REST API server (src/ghps/api.py, src/ghps/clusters.py)
- agentC owns API tests and integration (tests/test_api.py, tests/test_integration.py)
- Use python3 for all commands
- All API endpoints must return JSON

Merge Order
1. agentA-packaging-fixes
2. agentB-rest-api
3. agentC-api-tests

Merge Verification
- python3 -m pytest tests/ -v

## agentA-packaging-fixes

Objective
- Fix all Sprint 1 packaging and test bugs so the project installs and tests pass cleanly

Tasks
- Fix pyproject.toml: add [project.scripts] ghps = "ghps.cli:main"
- Fix editable install issue: ensure src layout works with pip install -e .
- Fix tests/test_embeddings.py import errors — mock sentence_transformers if needed for unit tests
- Fix tests/test_store.py import errors — mock sqlite_vec if needed for unit tests
- Ensure all 4 test files pass: test_github_client.py, test_embeddings.py, test_store.py, test_search.py
- Add .gitignore entries for .venv/, *.egg-info/, __pycache__/, .ghps/
- Add a Makefile or scripts for common operations: make install, make test, make index

Acceptance Criteria
- pip install -e ".[dev]" succeeds
- python3 -m pytest tests/ -v passes all tests
- ghps --help shows CLI usage
- .gitignore properly excludes build artifacts

## agentB-rest-api

Objective
- Build a FastAPI REST API with search, clusters, and repo detail endpoints

Tasks
- Add fastapi and uvicorn to pyproject.toml dependencies
- Create src/ghps/api.py with FastAPI app:
  - GET /api/search?q=<query>&top_k=10 — semantic search, returns ranked results with repo name, description, score, snippet, url
  - GET /api/clusters — capability clusters grouped by embedding similarity
  - GET /api/repos/<slug> — repo detail with metadata, README excerpt, matched chunks
  - GET /api/health — health check endpoint
  - CORS middleware for browser access
- Create src/ghps/clusters.py with:
  - ClusterEngine class that groups repos by embedding similarity
  - cluster_repos(store, n_clusters=10) -> list of Cluster(name, repos, centroid)
  - Use sklearn KMeans or simple cosine-similarity grouping
- Add [project.scripts] entry: ghps-server = "ghps.api:main" (uvicorn launcher)
- Server should accept --port, --db flags
- All responses follow consistent JSON format: {"ok": true, "data": ...} or {"ok": false, "error": "..."}

Acceptance Criteria
- python3 -m uvicorn ghps.api:app starts without errors
- GET /api/search?q=test returns valid JSON with results array
- GET /api/clusters returns grouped repos
- GET /api/repos/some-repo returns repo metadata
- CORS headers present in responses

## agentC-api-tests

Objective
- Write comprehensive API tests and an integration test that exercises the full pipeline

Tasks
- Create tests/test_api.py with:
  - Test /api/search returns results for known queries
  - Test /api/search with empty query returns error
  - Test /api/clusters returns non-empty clusters
  - Test /api/repos/<slug> returns 404 for unknown repos
  - Test /api/health returns ok
  - Use FastAPI TestClient (no server needed)
- Create tests/test_integration.py with:
  - End-to-end test: create temp store → add mock repos → search → verify results
  - Test that indexer + search pipeline produces correct rankings
  - Test deduplication (same repo, multiple chunks → one result per repo)
- Create tests/conftest.py with shared fixtures:
  - mock_store fixture — in-memory SQLite with test data
  - mock_github_responses fixture — cached API responses for testing

Acceptance Criteria
- python3 -m pytest tests/test_api.py -v passes
- python3 -m pytest tests/test_integration.py -v passes
- Integration test demonstrates full index → search pipeline
