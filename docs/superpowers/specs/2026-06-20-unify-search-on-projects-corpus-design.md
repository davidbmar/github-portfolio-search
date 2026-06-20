# Design — Unify Search on the Projects Corpus (Part 1)

**Session:** S-2026-06-20-0134-unify-search-projects-docs
**Status:** Approved (build Part 1, option A)

## Problem

`https://www.davidbmar.com/#/search?q=riff` finds nothing, and search results
have no connection to the rich `/projects/<slug>` pages. Root cause: the site
runs **two independent data pipelines**.

| | Search SPA (`#/search`) | Project pages (`/projects/`) |
|---|---|---|
| Data file | `repos.json` / `search-index.json` (**104**) | `projects.json` / `projects-index.json` (**132**) |
| Source | GitHub API (`ghps index`) | docsgen (LLM docs) |
| Has `riff`? | ❌ (private repo — GitHub API never lists it) | ✅ `/projects/riff` |

The search corpus is a stale **subset** of the project corpus. 28 projects —
including `riff` — have rich doc pages but are invisible to search. Search
results also link to an in-app `#/repo/<name>` view, never to `/projects/<slug>`.

## Principle

**docsgen (the 132-project corpus) becomes the single source of truth for
search.** Everything a user can find resolves to a static `/projects/<slug>`
page.

## Scope — Part 1 only (option A)

In scope:
1. **New docsgen artifact `web/data/projects-search.json`** — a search index
   built from all 132 projects' rich text (title, one_liner, what_it_is,
   how_its_built, how_to_apply, features, capabilities, components, patterns,
   tech, reuse_tags). Same shape the JS `SearchEngine.loadSearchIndex` already
   consumes: `[{repo, title, one_liner, keywords, chunks:[{source,text}]}]`,
   keyed by `repo = slug`.
2. **SPA searches the projects corpus.** `app.js` loads `projects-index.json`
   (132) as its primary corpus + `projects-search.json` for rich snippets,
   instead of `repos.json` / `search-index.json`.
3. **All results link to `/projects/<slug>`.** Every `#/repo/<name>` link
   becomes `/projects/<slug>` (slug == name for the 104 overlap; the 28 new
   ones are projects-only and already have pages).
4. **Remove the in-app `#/repo/<name>` detail view** (route + `renderRepo`).

Deferred (option A — explicitly NOT in this part):
- Clusters / similarity / suggestions stay built from the 104-repo embeddings.
  They degrade gracefully (the 28 new projects just don't appear in the graph
  yet). `clusters.json` keeps driving the homepage. Cluster repo links still
  resolve because slug == name.
- Part 2 (markdown doc capture, `/docs/html` listing) and Part 3 shorthand
  redirects are separate follow-ups.

## Data contract — `projects-search.json`

```json
{
  "generated_at": "…Z",
  "count": 132,
  "entries": [
    {
      "repo": "riff",
      "title": "Riff",
      "one_liner": "Voice agent platform that …",
      "keywords": ["voice-agent", "fsm", "python", …],   // tech + reuse_tags, lowercased
      "chunks": [
        {"source": "one_liner", "text": "Voice agent platform that …"},
        {"source": "what_it_is", "text": "…"},
        {"source": "features", "text": "…"}
      ]
    }
  ]
}
```

`SearchEngine.loadSearchIndex` currently expects a top-level **array**. To stay
backward-compatible with the JS, the file's payload is the array of entries
(the SPA reads `payload.entries ?? payload`). Snippet extraction in
`getSnippet` consumes `chunks[].text` exactly as today.

## SPA corpus normalization (app.js)

Each `projects-index.json` entry becomes a normalized "repo" object so the
existing `SearchEngine.search` / facets / rendering keep working:

```js
{
  name: p.slug,                       // chunk-map key + name match
  slug: p.slug,
  title: p.title,
  description: p.one_liner,
  topics: [...(p.tech||[]), ...(p.reuse_tags||[])],
  repo_url: p.repo_url,
  updated_at: p.pushed_at,
  thin: p.thin,
  stars: 0,
}
```

Result cards display `title`; the card links to `/projects/<slug>`.

## Build wiring

`docsgen/generate.py::render_all` gains one write next to `projects-index.json`:
`build_search_index(projects)` → `web/data/projects-search.json`. No LLM calls;
pure projection of records already in memory.

## Testing

- **pytest (TDD):** `build_search_index` — covers field inclusion, slug keying,
  lowercased keywords, chunk sources, empty/thin records, and a regression that
  a private project like `riff` is present.
- **Playwright (`test_web_playwright.py`):** searching `riff` yields ≥1 result
  whose link points to `/projects/riff`; `#/repo/...` route no longer renders a
  detail view.

## Success criteria

- `?q=riff` returns the Riff project.
- Search covers all 132 projects.
- Every result links to `/projects/<slug>`.
- No `#/repo/<name>` detail view remains.
- `make test` green.
