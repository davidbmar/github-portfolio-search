# Sprint 1

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

Merge Order
1. agentA-github-api
2. agentB-embedding-store
3. agentC-search-cli

Merge Verification
- python3 -m pytest tests/ -v

## agentA-github-api

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

## agentB-embedding-store

Objective
- Build the embedding pipeline and SQLite-vec vector store for indexing repo content

Tasks
- Create src/ghps/embeddings.py with:
  - EmbeddingPipeline class using sentence-transformers (all-MiniLM-L6-v2)
  - embed_text(text: str) -> list[float] (384-dim vector)
  - embed_batch(texts: list[str]) -> list[list[float]] for efficient batch processing
  - Chunk long documents (README + source files) into ~512 token segments
- Create src/ghps/store.py with:
  - VectorStore class wrapping SQLite-vec
  - create_index() -> sets up tables: repos (metadata), chunks (text + embedding), repo_files
  - add_repo(repo_dict, readme_text, source_files) -> indexes all content
  - Schema: repos table (name, description, language, topics JSON, stars, updated_at, url), chunks table (repo_name, source, text, embedding vec)
- Create src/ghps/indexer.py with:
  - Indexer class that ties together github_client + embeddings + store
  - index_user(username) -> fetches all repos, generates embeddings, stores in SQLite-vec
  - Progress logging (repo N/total, chunks generated)
- Create tests/test_store.py with unit tests (in-memory SQLite)
- Create tests/test_embeddings.py with basic embedding tests

Acceptance Criteria
- python3 -m pytest tests/test_store.py tests/test_embeddings.py passes
- VectorStore can insert and retrieve vectors by similarity
- EmbeddingPipeline produces 384-dim float vectors
- Indexer can process a list of repo dicts into the store

## agentC-search-cli

Objective
- Build the semantic search function and a basic CLI tool

Tasks
- Create src/ghps/search.py with:
  - SearchEngine class that wraps VectorStore + EmbeddingPipeline
  - search(query: str, top_k: int = 10) -> list of SearchResult(repo_name, chunk_text, score, source, repo_url)
  - Results sorted by cosine similarity score descending
  - Deduplicate results from same repo (return best-scoring chunk per repo)
- Create src/ghps/cli.py with:
  - Click-based CLI: ghps search "query" [--top-k N] [--db PATH]
  - ghps index <username> [--db PATH] [--token TOKEN]
  - Pretty-print results: repo name, score, snippet (first 200 chars), URL
  - Default db path: ~/.ghps/index.db
- Create pyproject.toml [project.scripts] entry: ghps = "ghps.cli:main"
- Create tests/test_search.py with unit tests (mock store with known vectors)

Acceptance Criteria
- python3 -m pytest tests/test_search.py passes
- search() returns results ranked by relevance score
- CLI ghps search prints formatted results to stdout
- CLI ghps index triggers indexing for a given username
