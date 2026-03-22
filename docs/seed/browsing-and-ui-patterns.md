# Browsing and UI Patterns: GitHub Portfolio Search

## Design Philosophy

Search and browse are complementary. Not every visit starts with a query — sometimes users want to explore. The UI should support three modes:

1. **Search** — type a query, get ranked results
2. **Browse** — explore visually by capability, tech stack, or time
3. **Filter** — narrow results using facets (works with both search and browse)

## Visual Capability Tree (Circle Packing / Treemap)

Inspired by GitHub Next's repo visualization (React + D3.js circle packing).

### Concept
A visual map showing all ~90 repos grouped by capability domain. Each cluster is a circle (or rectangle in treemap) sized by repo count. Click to drill in, click a repo to see details.

### Layout
```
Top level:
[Voice/STT/TTS (20)] [Transcription (10)] [Browser AI (8)]
[Auth/Identity (6)]  [Tools (8)]          [Bots/Agents (5)]
[Deploy/Infra (5)]   [Other]

Drill into Voice:
[Whisper (4)] [NVIDIA ASR (6)] [Browser STT/TTS (3)]
[Voice Agents (4)] [Voice Infra (3)]

Drill into a repo:
README preview, tech stack tags, last activity, maturity badge
```

### Interactions
- Hover: show repo name + one-line description
- Click cluster: drill into sub-categories
- Click repo: open detail panel (README, file tree, snippets if authed)
- Breadcrumb trail: Voice > Whisper > whisperX-runpod

### Benefits
- No query needed — just explore
- Immediately communicates breadth and depth of work
- Works great as a public portfolio landing page
- Capability clusters are auto-generated from embeddings (not manually tagged)

## Faceted Search / Filtering

Inspired by Algolia faceted navigation and A List Apart's design patterns.

### Facets

| Facet | Type | Values |
|---|---|---|
| Capability | Multi-select chips | Voice, Auth, Browser AI, Tools, Bots, Infra, Transcription, Deploy |
| Tech Stack | Multi-select chips | Python, JavaScript/TypeScript, AWS, Cloudflare, React, Docker |
| Language | Multi-select | Python, JavaScript, TypeScript, Bash, Go |
| Last Active | Range / preset | This week, This month, This quarter, This year, Older |
| Maturity | Single-select | Active (commits < 30d), Stable (commits < 90d), Dormant (> 90d), Prototype (< 10 commits) |
| Visibility | Toggle | Public, Private (only in authenticated view) |
| Has Tests | Toggle | Yes / No |
| Has Docs | Toggle | Yes / No |

### UX Rules (from best practices research)
1. Show facets alongside search results, not on a separate page
2. Show count next to each facet value: `Python (34)` `AWS (22)`
3. Only show facet values that have results (no dead ends)
4. Allow multiple selections within a facet (OR logic within, AND across)
5. Clear "reset filters" always visible
6. Facets persist across searches until explicitly cleared

### Combined with Search
- Type "voice" in search box -> results appear
- Click "AWS" facet -> filters to voice repos using AWS
- Click "Last 3 months" -> further filters to recent voice+AWS repos
- Clear search -> still shows AWS repos from last 3 months (facets persist)

## Activity Timeline / Heatmap

### Concept
A GitHub-style contribution heatmap but for repos. Shows which repos had commits/activity during which time periods.

### Views

**Timeline view:**
```
Jan 2026  |████░░░░| whisperX-runpod
          |░░░░░░░░| auth0-s3-backend
          |██████░░| grassy-knoll
Feb 2026  |░░░░████| transcription-sqs
          |████████| bot-customerObsessed
          |██░░░░░░| tool-telegram-whatsapp
Mar 2026  |████████| github-portfolio-search (this project!)
```

**Heatmap view (by month x capability):**
```
         Jan  Feb  Mar
Voice    ███  ██░  ░░░
Auth     ░██  ░░░  ░░░
Tools    ░░░  ███  ███
Bots     ░░░  ███  ██░
```

### Interactions
- Click a time range: filter all views to that period
- Hover a bar: show commit count + key changes
- Toggle between "all activity" and "meaningful activity" (exclude bot commits, CI)

## Search Results Layout

### Result Card
Each search result should show:
```
┌──────────────────────────────────────────────┐
│ ★ S3-presignedURL-Lambda-APIGateway-setup    │
│ ┌────────┐ ┌─────┐ ┌────┐ ┌───────────────┐ │
│ │ Python │ │ AWS │ │ S3 │ │ Last: 2 mo ago│ │
│ └────────┘ └─────┘ └────┘ └───────────────┘ │
│                                              │
│ Presigned URL generation for S3 uploads via  │
│ API Gateway + Lambda. Handles multipart...   │
│                                              │
│ ┌─ Matching snippet ────────────────────┐    │
│ │ def generate_presigned_url(bucket,    │    │
│ │     key, expiration=3600):            │    │
│ │     return s3.generate_presigned_url( │    │
│ └───────────────────────────────────────┘    │
│ 📂 View files  🔗 GitHub  📊 12 commits     │
└──────────────────────────────────────────────┘
```

### Relevance Indicators
- Semantic match score (how well it matches the query intent)
- Freshness indicator (last commit date)
- Maturity badge (active / stable / prototype)
- Match source icon (README match vs. code match vs. dependency match)

## Mobile Considerations

The public portfolio should work on mobile:
- Capability tree collapses to a vertical list on small screens
- Facets move to a slide-out filter panel
- Search results stack vertically
- Code snippets scroll horizontally

## Inspiration / References

- GitHub Next repo visualization: circle packing with D3.js
- Sourcegraph: code search with file-type and repo facets
- Algolia InstantSearch: real-time faceted search UI components
- npm search: package cards with metadata badges
- GitHub contribution heatmap: activity over time visualization
