agentB-enhanced-search — Sprint 17

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
- Upgrade the client-side search engine with TF-IDF scoring and chunk text matching

Tasks
- Update web/js/search.js:
  - Add a `loadSearchIndex(data)` method to the SearchEngine namespace:
    - Accepts the parsed search-index.json array
    - Builds an inverted index: term -> Set of repo names (for IDF calculation)
    - Builds a per-repo chunk text map: repo_name -> concatenated chunk text
    - Stores the total number of repos (N) for IDF computation
  - Add TF-IDF scoring to the `search()` method:
    - When search index is loaded, compute IDF weight for each query term: log(N / df) where df = number of repos containing the term
    - Multiply the existing field-match points by the IDF weight
    - This means rare terms (appearing in few repos) get much higher scores than common terms
  - Add chunk text matching to the `search()` method:
    - When search index is loaded, check if query terms appear in the repo's chunk text
    - Award 2 points per term found in chunk text (README and source file content)
    - Apply IDF weighting to chunk matches as well
  - Add a `getSnippet(repoName, query)` method:
    - Looks up the repo's chunks from the loaded search index
    - Finds the chunk whose text best matches the query terms (most term matches)
    - Returns a ~200 char excerpt centered on the first match, or null if no match
    - Does NOT do HTML escaping (caller handles that)
  - Ensure backward compatibility:
    - If loadSearchIndex() was never called, search() works exactly as before
    - All new code paths are guarded by checking if the inverted index exists

Acceptance Criteria
- SearchEngine.loadSearchIndex(data) builds inverted index from search-index.json
- Searching "presigned URL" ranks repos with those terms in README chunks higher
- SearchEngine.getSnippet("S3-presignedURL", "presigned URL") returns a relevant text excerpt
- Search still works identically when search index is not loaded (backward compat)
- TF-IDF weighting boosts rare terms ("presigned") over common terms ("python")
- No global variable pollution (everything stays in SearchEngine namespace)
