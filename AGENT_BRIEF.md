agentC-ui-autocomplete — Sprint 17

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
