# Sprint 18

Goal
- Shareable search result links (deep links with query + filters in URL)
- Export search results as markdown or JSON
- "Collections" — save groups of repos as named lists (localStorage)
- Public portfolio embed widget (iframe-embeddable mini view)

Constraints
- No two agents may modify the same files
- agentA owns sharing/deep links (web/js/app.js)
- agentB owns collections feature (web/js/collections.js — NEW, web/css/style.css)
- agentC owns export + embed widget (web/embed.html — NEW, web/js/export.js — NEW, web/index.html)
- Use python3 for all commands
- Do NOT commit .venv/ or .env to git
- All features must work in static mode (no API server required)
- Use localStorage for persistence (no backend needed)

Merge Order
1. agentA-sharing
2. agentB-collections
3. agentC-export-embed

Merge Verification
- python3 -m pytest tests/ -v

## agentA-sharing

Objective
- Make search URLs shareable and persist filter state in the URL

Tasks
- Update web/js/app.js:
  - Persist filter state in URL hash parameters:
    - Current: #/search?q=voice
    - New: #/search?q=voice&lang=Python,Shell&topic=aws,whisper&stars=1&sort=recent
    - When filters change, update the hash (replaceState to avoid history spam)
    - When page loads with filter params, restore them
  - Add a "Share" button next to the sort dropdown on search results page:
    - Clicking copies the current URL (with query + filters) to clipboard
    - Show brief "Link copied!" toast notification (2s, then fade)
  - Add a "Share" button on repo detail pages:
    - Copies the #/repo/name URL to clipboard
  - Implement a simple toast notification system:
    - Create a showToast(message) function
    - Toast appears at bottom-center, auto-dismisses after 2s
    - Style: dark background, white text, rounded, subtle slide-up animation
  - Ensure deep links work:
    - Visiting #/search?q=voice&lang=Python should show search results filtered to Python repos matching "voice"
    - Visiting #/repo/voice-print should show the repo detail page

Acceptance Criteria
- Search URL includes query, language filters, topic filters, min stars, and sort mode
- Sharing a URL and opening it in a new tab shows the same results with same filters
- "Share" button copies URL to clipboard and shows toast
- Repo detail pages have a share button
- Filter changes update the URL without adding history entries
- python3 -m pytest tests/ -v passes

## agentB-collections

Objective
- Let users save groups of repos as named collections in localStorage

Tasks
- Create web/js/collections.js:
  - CollectionsManager namespace (IIFE pattern, like SearchEngine):
    - Storage key: "ghps_collections" in localStorage
    - Data format: { collections: [ { name: "My AI Projects", repos: ["repo1", "repo2"], created: "ISO date" } ] }
    - Functions:
      - getAll() → returns all collections
      - create(name) → creates new empty collection, returns it
      - addRepo(collectionName, repoName) → adds repo to collection
      - removeRepo(collectionName, repoName) → removes repo from collection
      - deleteCollection(name) → deletes entire collection
      - getCollection(name) → returns single collection
    - All functions persist to localStorage immediately
  - Export via global CollectionsManager and module.exports
- Update web/css/style.css:
  - Style .collections-panel: sidebar or modal for managing collections
  - Style .collection-card: card showing collection name, repo count, created date
  - Style .add-to-collection-btn: small button on repo cards and detail pages
  - Style .collection-detail: list of repos in a collection with remove buttons
  - Style .collections-nav-link: nav bar link to collections page
  - Mobile-friendly: full-width on small screens
- Note: agentB must NOT modify app.js or index.html (those belong to agentA and agentC)

Acceptance Criteria
- CollectionsManager.create("My Projects") creates a collection
- CollectionsManager.addRepo("My Projects", "voice-print") adds a repo
- Collections persist across page refreshes (localStorage)
- CollectionsManager.getAll() returns all collections with repo lists
- Deleting a collection removes it from localStorage
- CSS styles exist for collections UI components
- python3 -m pytest tests/ -v passes

## agentC-export-embed

Objective
- Export search results and create an embeddable portfolio widget

Tasks
- Create web/js/export.js:
  - ExportManager namespace (IIFE pattern):
    - exportAsMarkdown(results, query) → generates markdown string:
      ```
      # Search Results: "query"

      ## repo-name
      - **Language:** Python
      - **Stars:** 5
      - **Description:** ...
      - **GitHub:** https://github.com/...
      - **Topics:** aws, voice, ...

      ---
      ```
    - exportAsJSON(results, query) → generates JSON string with repos array
    - downloadFile(content, filename, mimeType) → triggers browser file download
  - Export via global ExportManager and module.exports
- Create web/embed.html:
  - Standalone HTML page that renders a mini portfolio view
  - Loads repos.json and clusters.json from data/ directory
  - Shows: portfolio title, repo count, top 5 clusters, top 10 repos by relevance
  - Compact styling (no nav bar, no search, just a browsable snapshot)
  - Designed to be embedded via iframe: <iframe src="https://davidbmar.com/embed.html" width="400" height="600"></iframe>
  - Add a "View full portfolio" link to the main site
  - Self-contained: inline CSS, no external dependencies except data files
  - Security: set appropriate X-Frame-Options considerations in comments
- Update web/index.html:
  - Add <script src="js/collections.js"></script> before app.js
  - Add <script src="js/export.js"></script> before app.js
  - Add a "Collections" link in the nav bar (href="#/collections")

Acceptance Criteria
- ExportManager.exportAsMarkdown(results, "voice") returns valid markdown
- ExportManager.exportAsJSON(results, "voice") returns valid JSON
- ExportManager.downloadFile() triggers a browser download
- embed.html loads and renders portfolio summary standalone
- embed.html works in an iframe without errors
- index.html includes script tags for collections.js and export.js
- Nav bar includes Collections link
- python3 -m pytest tests/ -v passes
