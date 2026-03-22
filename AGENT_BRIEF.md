agentA-export-data — Sprint 17

Sprint-Level Context

Goal
- Upgrade web UI from keyword-only search to TF-IDF + chunk-text matching using search-index.json
- Add embedding-powered "related repos" via pre-computed similarity matrix
- Add autocomplete/search suggestions dropdown
- Improve search result snippets with README excerpts

Constraints
- No two agents may modify the same files
- agentA owns the export pipeline (src/ghps/export.py, tests/test_export.py)
- agentB owns the JS search engine (web/js/search.js)
- agentC owns the UI integration (web/js/app.js, web/index.html, web/css/style.css)
- Use python3 for all commands
- Do NOT commit .venv/ or .env to git
- All features must work in static mode (no API server required)
- Web UI loads data from web/data/ JSON files only


Objective
- Enhance the export pipeline to produce richer data files for the web UI

Tasks
- Update src/ghps/export.py:
  - In _build_repos() (or equivalent), add a `readme_excerpt` field to each repo dict:
    - Query the chunks table for the first README chunk per repo
    - Truncate to 300 chars
    - If no README chunk exists, use empty string
  - Create a new function _build_similarity() that:
    - Computes the average embedding vector per repo (average of all chunk embeddings)
    - Calculates pairwise cosine similarity between all repo average embeddings
    - For each repo, keeps the top-8 most similar repos with their scores
    - Returns a dict: {"repo_name": [{"name": "other_repo", "score": 0.85}, ...]}
    - Uses numpy for efficient vector operations (already a dependency via sentence-transformers)
  - Create a new function _build_suggestions() that:
    - Collects all repo names from the store
    - Collects all unique topics across repos
    - Tries to read top-20 popular queries from analytics DB (~/.ghps/analytics.db)
    - If analytics DB doesn't exist, uses empty queries list (graceful fallback)
    - Returns a dict: {"repos": [...], "topics": [...], "queries": [...]}
  - Update export_static_bundle() to:
    - Call _build_similarity() and write result to web/data/similarity.json
    - Call _build_suggestions() and write result to web/data/suggestions.json
    - Ensure readme_excerpt is included in repos.json output
- Update tests/test_export.py:
  - Test that repos.json entries include readme_excerpt field
  - Test _build_similarity() returns correct format with scores between 0 and 1
  - Test _build_suggestions() returns correct format
  - Test _build_suggestions() works when analytics DB doesn't exist
  - Test similarity matrix has at most 8 entries per repo

Acceptance Criteria
- repos.json entries include `readme_excerpt` (string, up to 300 chars)
- similarity.json exists with top-8 similar repos per repo, each with a float score
- suggestions.json exists with repos, topics, and queries arrays
- Export works when analytics DB doesn't exist (no crash)
- python3 -m pytest tests/test_export.py -v passes
