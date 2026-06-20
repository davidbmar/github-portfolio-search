# Design — Per-Project Docs Browsing + Cross-Linking (Parts 2 & 3)

**Session:** S-2026-06-20-0134-unify-search-projects-docs
**Status:** Built. Follows Part 1 (search unification).

## Goal

Let a visitor browse a project's documentation — `/riff/docs` shows every doc
(HTML and Markdown), `/riff/docs/html` lists the HTML docs, `/riff/docs/md`
lists the Markdown — and make the whole site one continuous click-path:
**search → project page → docs → individual doc → GitHub**.

## Part 2 — Per-project docs browsing

### Capture (was: HTML only)
- `github_client.fetch_markdown_docs` mirrors `fetch_html_docs`: an explicit
  opt-in folder `docs/md/**/*.md` (symmetric with `docs/html/`). Both now share
  one tree-walk engine `_fetch_docs_under(prefix, suffix)`.
- `context.RepoContext.md_docs` carries `(path, raw_markdown)` tuples;
  `build_context` fetches them defensively (`getattr`, so old gh doubles work).
- `record_gen` adds Markdown entries to the record's `docs` array as
  `{"path", "kind": "md", "markdown": <raw>}`. HTML entries keep their existing
  `{"path", "html"}` shape (no `kind`) — purely additive, no migration.

### Render
- New zero-dependency, **escape-safe** Markdown renderer
  `docsgen/markdown.py::render`. Escapes all text first, emits a known-safe tag
  subset (headings, fenced code, lists, blockquote, hr, paragraphs, inline
  bold/italic/code/links). Raw HTML in a doc is escaped, not passed through;
  unsafe link schemes (`javascript:`) are dropped. Matches the repo's
  minimal-deps, escape-into-`<pre>` house style.
- `render.render_markdown_doc_page(record, rel, body_html)` wraps rendered
  Markdown in a styled page with nav: ← project · Docs · View on GitHub.
- `render.render_docs_index_page(record, html_rels, md_rels=None)` — extended
  (optional `md_rels`, backward-compatible) to a combined index grouped by kind,
  each group linking to its dedicated listing page.
- `render.render_docs_kind_page(record, kind, rels)` — a single-kind listing.

### Publish (`generate.publish_all`)
Site layout under `web/projects/<slug>/`:
```
docs/index.html        combined index (grouped: HTML / Markdown)
docs.html              flat copy (so /docs resolves without trailing slash)
docs/html.html         HTML listing      -> served at /docs/html
docs/md.html           Markdown listing  -> served at /docs/md
docs/<rel>.html        HTML docs (verbatim, unchanged location)
docs/md/<rel>.html     Markdown docs (rendered)
```
`_safe_md_rel` strips `docs/md/`, rejects traversal, maps `*.md` → `*.html`.
HTML doc URLs are unchanged (no breakage); Markdown is namespaced under
`docs/md/` so `/docs/html` and `/docs/md` are clean, symmetric listings.

## Part 3 — Cross-linking / integration

The continuous path, all verified live:
- Search result card → `/projects/<slug>.html`           (Part 1)
- Project page → `/projects/<slug>/docs/`                 (existing docs-link, now also fires for md-only projects)
- Combined index → `/docs/html`, `/docs/md`, individual docs
- Markdown doc page → back to project, docs, and source repo on GitHub

### Shorthand `/<slug>/docs` (infra)
Requires the deployed CloudFront Function (not owned by this repo). Source to
paste is committed at `infra/cloudfront/url-rewrite.js`:
- rewrites `/<slug>/docs[/...]` → `/projects/<slug>/docs[/...]` with a
  RESERVED-prefix guard so real top-level paths (`/data`, `/js`, …) are untouched;
- keeps the existing extensionless → `.html` behavior that already makes
  `/projects/<slug>/docs`, `/docs/html`, `/docs/md` resolve.
Logic unit-tested via node (9 cases). **Not deployed** from here — deploy + test
in the CF console before relying on the shorthand. Everything else works today.

## Deploy safety (Part 1 follow-through)
`deploy.sh` now also validates `projects-index.json` (≥1 `projects`) and
`projects-search.json` (≥1 `entries`) — the files the SPA hard-depends on after
Part 1 — failing the deploy fast if either is missing or malformed.

## Testing
- `markdown.render` — 11 cases incl. XSS/escaping + unsafe-scheme.
- `fetch_markdown_docs` — folder/suffix filtering, missing tree.
- context/record — md docs carried + recorded as raw source.
- render — combined index grouping, per-kind listing, markdown doc page nav.
- `publish_all` — renders md, writes kind listings, rejects md traversal.
- Verified live (Playwright): combined index grouping, rendered markdown
  (bold/code/lists/blockquote/links, no raw leak), project→docs link.
- `make test`: full suite green.

## Success criteria
- `/projects/<slug>/docs` shows HTML + Markdown grouped.
- `/projects/<slug>/docs/html` and `/docs/md` list each kind.
- Markdown docs render to safe, styled, navigable pages.
- The search → project → docs → GitHub path has no dead ends.
