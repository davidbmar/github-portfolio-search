agentC-export-embed — Sprint 18

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
