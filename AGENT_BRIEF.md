agentA-github-api — Sprint 1

Sprint-Level Context

Goal
- Build the indexing pipeline that fetches all ~90 repos via GitHub API, generates embeddings with sentence-transformers, and stores them in SQLite-vec
- Deliver a working search function that returns ranked results with code snippets
- Establish the Python project structure with pyproject.toml and proper packaging

Constraints
- No two agents may modify the same files
- agentA owns project scaffold and GitHub API client (src/ghps/github_client.py, src/ghps/__init__.py, pyproject.toml)
- agentB owns embedding pipeline and vector store (src/ghps/embeddings.py, src/ghps/store.py)
- agentC owns search function and CLI (src/ghps/search.py, src/ghps/cli.py)
- Use python3 for all commands
- Use sentence-transformers for embeddings (all-MiniLM-L6-v2 model)
- Use sqlite-vec for vector storage


Objective
- Set up the Python project and build a GitHub API client that fetches all repos, READMEs, and metadata for a given user

Tasks
- Create pyproject.toml with dependencies: requests, sentence-transformers, sqlite-vec, click, pytest
- Create src/ghps/__init__.py with version
- Create src/ghps/github_client.py with:
  - fetch_repos(username) -> list of repo dicts (name, description, language, topics, stars, updated_at, html_url)
  - fetch_readme(owner, repo) -> str (README content, empty string if none)
  - fetch_top_files(owner, repo, extensions=['.py', '.js', '.ts', '.go', '.rs', '.java']) -> list of (path, content) tuples
  - Support GitHub token via GITHUB_TOKEN env var for authenticated requests (5000 req/hr)
  - Handle pagination for users with many repos
- Create tests/test_github_client.py with unit tests (mock HTTP responses)
- Create a .env.example showing GITHUB_TOKEN=ghp_xxx

Acceptance Criteria
- python3 -m pytest tests/test_github_client.py passes
- fetch_repos returns repo metadata for a user with >50 repos
- fetch_readme returns content for repos that have READMEs
- Authenticated requests use GITHUB_TOKEN when available
