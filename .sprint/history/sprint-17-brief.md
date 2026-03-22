# Sprint 17

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

Merge Order
1. agentA-export-data
2. agentB-enhanced-search
3. agentC-ui-autocomplete

Merge Verification
- python3 -m pytest tests/ -v

## agentA-export-data

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

## agentB-enhanced-search

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

## agentC-ui-autocomplete

Objective
- Wire together the new data files, autocomplete UI, similarity-based related repos, and snippet rendering

Tasks
- Update web/js/app.js:
  - In App.init() or the data loading section:
    - Fetch web/data/search-index.json and pass to SearchEngine.loadSearchIndex()
    - Fetch web/data/similarity.json and store as App.similarity
    - Fetch web/data/suggestions.json and store as App.suggestions
    - All three fetches should fail silently (existing behavior preserved if files missing)
  - Replace findRelatedRepos() implementation:
    - If App.similarity exists and has data for the repo, use it to return top-N similar repos
    - Map similarity entries back to full repo objects from App.repos
    - Update the "Related Repositories" label from "from same cluster" to "Semantically similar"
    - Fall back to cluster-based lookup if similarity data unavailable
  - Add autocomplete functionality:
    - Create a renderAutocomplete(inputElement) function
    - On input event, filter App.suggestions entries matching current text (case-insensitive prefix)
    - Combine matches from repos, topics, and queries arrays
    - Show top-8 matches in a dropdown div positioned below the search input
    - Handle keyboard: ArrowDown/ArrowUp to navigate, Enter to select, Escape to close
    - Handle mouse: click to select
    - Handle blur: close dropdown after short delay (allow click events to fire first)
    - Call renderAutocomplete() on the search input after init
  - Update search result rendering:
    - After getting search results, call SearchEngine.getSnippet(repo.name, query)
    - If a snippet is returned, display it (with highlighted terms) below the description
    - If no snippet, fall back to repo.description as before
    - Escape HTML in snippets before inserting (use existing escapeHtml function)
- Update web/index.html:
  - Add a container div for autocomplete dropdown adjacent to the search input
  - Ensure the search input wrapper has position: relative for dropdown positioning
- Update web/css/style.css:
  - Style .autocomplete-dropdown: absolute position, white background, border, shadow, z-index, max-height with overflow-y scroll
  - Style .autocomplete-item: padding, hover highlight, cursor pointer
  - Style .autocomplete-item.active: background highlight for keyboard-selected item
  - Style .search-snippet: smaller font, muted color, max 3 lines with ellipsis overflow
  - Ensure autocomplete works on mobile (full width, touch-friendly tap targets)

Acceptance Criteria
- Typing in search shows autocomplete dropdown with matching suggestions
- Arrow keys navigate suggestions, Enter selects, Escape closes
- Clicking a suggestion navigates to search results for that term
- Related repos section shows embedding-similar repos from similarity.json
- Related repos falls back to cluster-based if similarity.json not loaded
- Search results show README snippet excerpts with highlighted query terms
- All features degrade gracefully if data files are missing
- No XSS — all user input and snippet text is escaped before DOM insertion
- Mobile-friendly autocomplete (full-width, adequate tap targets)
