# Session

Session-ID: S-2026-06-20-0134-unify-search-projects-docs
Title: Unify search on the projects corpus (Part 1)
Date: 2026-06-20
Author: David Mar (with Claude)

## Goal

Make `#/search` find every project (including private ones like `riff`) and
link results to the rich `/projects/<slug>` pages — by making the docsgen
projects corpus the single source of truth for search.

## Context

The site runs two disconnected pipelines: `repos.json`/`search-index.json`
(104 public repos, from the GitHub API) drives search; `projects.json`/
`projects-index.json` (132 projects, from docsgen) drives the project pages.
`riff` is a **private** repo, so the GitHub API never lists it — it exists only
in the docsgen corpus, which is why `?q=riff` returns nothing. Search results
also link to an in-app `#/repo/<name>` view, orphaning the `/projects/` pages.

## Plan

Part 1 (option A — defer the clusters/similarity graph):
1. docsgen emits `web/data/projects-search.json` — a rich search index over all
   132 projects, in the shape the JS `SearchEngine` already consumes.
2. `app.js` searches the projects corpus (`projects-index.json` +
   `projects-search.json`) instead of `repos.json`.
3. All `#/repo/<name>` links → `/projects/<slug>`.
4. Remove the `#/repo` detail route/render.

TDD the Python `build_search_index`; verify the SPA with Playwright.

Spec: `docs/superpowers/specs/2026-06-20-unify-search-on-projects-corpus-design.md`

## Changes Made

**Server (docsgen):**
- New `src/ghps/docsgen/search_index.py` — `build_search_index(projects)` /
  `write_search_index(...)`. Projects each record to a search entry keyed by
  slug, with lowercased `keywords` (tech + reuse_tags) and prose `chunks`
  (title, one_liner, what_it_is, how_its_built, how_to_apply, features). TDD'd
  (`tests/test_docsgen_search_index.py`, 9 cases incl. a private-project
  regression).
- `docsgen/generate.py::publish_all` now also writes
  `web/data/projects-search.json` next to `projects-index.json`. Test in
  `test_docsgen_generate.py::test_publish_all_writes_search_index`.
- Generated `web/data/projects-search.json` (132 entries) from existing records.

**Client (web/js/app.js):**
- `loadData` now loads `projects-index.json` (132, searchable corpus) +
  `projects-search.json` (rich chunks) instead of `repos.json` /
  `search-index.json`. `repos.json` kept as a **metadata sidecar** — GitHub-only
  `updated_at`/`language`/`stars` left-joined by slug == name so the homepage
  recency/language/stars don't regress (105/132 get a date, 104 a language).
- Added `projectHref()` / `projectTitle()`; all result/card/recent links now go
  to `/projects/<slug>.html` and show the project title.
- Removed the in-app detail view: deleted `renderRepoDetail`,
  `findClusterForRepo`, `_getRepoReadme` (215 lines). Legacy `#/repo/<name>`
  now redirects to the static page.

**Verified (Playwright, local server):**
- `?q=riff` → 1 result "Riff" → `/projects/riff.html` (was 0 before).
- `?q=voice agent` → 54 results, all with snippets, all → `/projects/`.
- `#/repo/riff` → redirects to `/projects/riff.html`.
- Homepage: 10 recent items, 8 language rows, 6 clusters — no regression.
- `make test`: 396 passed, 1 skipped. `make lint`: clean.

**Part 2 — per-project docs browsing (md capture + listings):**
- `github_client.fetch_markdown_docs` (+ shared `_fetch_docs_under` engine) —
  captures `docs/md/**/*.md` (opt-in folder, symmetric with `docs/html/`).
- `context.RepoContext.md_docs` + `build_context` fetch (defensive `getattr`).
- `record_gen` records md docs as `{path, kind:"md", markdown:<raw>}`; html docs
  keep `{path, html}` (additive, no migration).
- New zero-dep, escape-safe `docsgen/markdown.py::render` (XSS-safe: escapes all
  text, drops `javascript:` links, no raw-HTML passthrough). 11 tests.
- `render.render_markdown_doc_page`, `render_docs_kind_page`, and
  `render_docs_index_page(html_rels, md_rels=None)` grouped by kind.
- `publish_all` writes `docs/index.html`(+flat `docs.html`), `docs/html.html`,
  `docs/md.html`, html docs at `docs/<rel>`, rendered md at `docs/md/<rel>`.
  `_safe_md_rel` maps `docs/md/x.md`→`x.html`, rejects traversal.

**Part 3 — cross-linking:**
- Continuous path verified live: search → `/projects/<slug>.html` → `/docs/` →
  `/docs/html` · `/docs/md` → individual doc → GitHub.
- `infra/cloudfront/url-rewrite.js` — CF Function source for the `/<slug>/docs`
  shorthand (RESERVED-guard) + extensionless→.html. Logic unit-tested via node
  (9 cases). NOT deployed from here — paste into CF distribution E3RCY6XA80ANRT.
- `deploy.sh` now validates `projects-index.json` + `projects-search.json`
  (SPA hard-deps after Part 1) — fail-fast deploy guard.

**Verified (Playwright):** combined docs index groups HTML(1)/Markdown(2) with
per-kind "view all" links; rendered markdown page shows bold/code/lists/
blockquote/hr/links with no raw `**` leak + nav to project/docs/GitHub; project
page shows "📄 Project documentation (3 docs) →" → `/docs/`.

## Known follow-ups (out of scope for Part 1)

- Most `projects-index.json` records have `pushed_at: null` (only riff). The
  sidecar masks this on the homepage today; a proper fix is docsgen backfilling
  `pushed_at` for all records (needs a re-run with GitHub access).
- Option B (re-index all 132 so clusters/similarity unify) — later part.
- Part 2 (markdown doc capture, `/docs/html` listing) — later part.

## Decisions Made

- **docsgen corpus is the source of truth for search**, not the GitHub-API
  index — it's the superset (132 ⊃ 104) and includes private/shipped projects.
- **Option A**: leave clusters/similarity on the 104-repo embeddings for now;
  unify the graph in a later part. Keeps Part 1 shippable.
- **Remove** the `#/repo` view rather than redirect (user's choice).

## Open Questions

- Part 2 (markdown doc capture + `/docs/html` listing) and graph re-indexing
  (option B) are follow-ups.

## Links

Commits:
- (pending)

PRs:
- (pending)

ADRs:
- (none yet)
