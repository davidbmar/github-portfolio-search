agentB-collections — Sprint 18

Sprint-Level Context

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
