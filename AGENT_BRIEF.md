agentC-search-cli — Sprint 1

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
