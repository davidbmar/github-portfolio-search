agentA-sharing — Sprint 18

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
