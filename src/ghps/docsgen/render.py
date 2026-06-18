"""Render a structured record into a self-contained HTML page.

Pure Python (no Jinja). All record fields are LLM-authored and therefore treated
as UNTRUSTED (a prompt-injected README could steer the model's output):

  - Prose fields are html.escape'd.
  - Mermaid diagram source must stay human-readable to render, so it is NOT fully
    escaped — but `<` is escaped to `&lt;` (see `_mermaid`) to prevent a
    `</pre><script>` breakout. Arrow syntax (`-->`, `->>`) has no `<`, so diagrams
    still render; the browser decodes `&lt;` back to `<` in the element's
    textContent, which is what Mermaid reads.
  - Both `<script>` JSON blocks (the #project-data island and the JSON-LD block)
    apply `.replace("</", "<\\/")` so a field containing `</script>` cannot
    terminate the tag early. `<\\/` is valid JSON.

Each page embeds a JSON data island and a JSON-LD SoftwareSourceCode block so
machine-readability falls out for free.
"""

from __future__ import annotations

import html
import json
import re

# Use the ESM module build (.mjs) — the .min.js is a UMD bundle with no default
# export, so `import mermaid from ...` silently fails and diagrams never render.
# Pinned for reproducibility.
_MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs"


def _mermaid(src: str) -> str:
    """Make Mermaid source safe to embed raw in <pre> without breaking rendering.

    Escapes only ``<`` (to ``&lt;``) so a payload like ``</pre><script>`` cannot
    break out of the <pre> element. Mermaid arrow syntax contains no ``<``, and
    the browser decodes ``&lt;`` back to ``<`` in textContent before Mermaid reads
    it, so legitimate diagrams are unaffected.

    Also drops empty parens: LLM-authored diagrams often use function-call
    notation in node labels (``run_turn()``), and Mermaid's flowchart parser
    errors on ``(`` inside a ``[..]`` label — the red "syntax error" icon. Empty
    parens carry no meaning in valid Mermaid, so removing them is a safe net
    (the model is also told to avoid parens in labels; see record_gen._SYSTEM).
    """
    return src.replace("()", "").replace("<", "&lt;")


def _json_script(data) -> str:
    """Serialize *data* for embedding inside a <script> tag without breakout."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_llms_txt(projects: list[dict], *, base_url: str, generated_at: str) -> str:
    """Render the /llms.txt discovery manifest (progressive disclosure entry point).

    Tiny on purpose: it tells an agent where the structured data is and how to pull
    only what it needs, instead of loading all records into context.
    """
    base = base_url.rstrip("/")
    n = len(projects)
    return f"""# davidbmar.com — Project Portfolio

> AI-generated, machine-readable documentation for {n} of David Mar's GitHub
> projects. Each project covers what it is, how it's built (with architecture +
> sequence diagrams), and how to apply/reuse it, plus typed metadata
> (capabilities, tech, patterns, reuse_tags) for "have we built X?" queries.

## How to use this efficiently (progressive disclosure — do NOT load everything)

1. Scan the COMPACT index first (small — slug, title, one_liner, tech, reuse_tags):
   {base}/data/projects-index.json
   Use it to pick the few projects relevant to your question.
2. Fetch the FULL record for ONLY those slugs:
   {base}/projects/<slug>.record.json
   (full prose, Mermaid diagrams, components, depends_on, integrates_with, hygiene)
3. Human-readable page for a project:
   {base}/projects/<slug>.html
4. Browse all projects (humans): {base}/projects/

## Query interface for agents (search, don't download)

MCP server `ghps-mcp` exposes `portfolio_find_docs(query)` — returns ranked matches
(slug, title, one_liner, the fields that matched). Prefer this over downloading the
full corpus when you only need a few results.

## Full corpus (last resort — only if you genuinely need every record at once)

{base}/data/projects.json

## Field semantics

- reuse_tags, capabilities, patterns: best signals for "have we built X / can I reuse Y?"
- tech, depends_on, integrates_with: stack and dependencies
- thin=true: fork / stub / empty repo — low signal, may be skipped

Generated {generated_at} · {n} projects.
"""


def _tags(items: list[str]) -> str:
    if not items:
        return '<span class="muted">—</span>'
    return "".join(f'<span class="tag">{html.escape(t)}</span>' for t in items)


def _meta_row(label: str, items: list[str]) -> str:
    return (
        f'<div class="meta-row"><span class="meta-label">{html.escape(label)}</span>'
        f'<span class="meta-tags">{_tags(items)}</span></div>'
    )


def _hygiene_panel(record: dict) -> str:
    todos = record.get("todos", [])
    if not todos:
        return '<section class="hygiene clean"><h2>Repo hygiene</h2><p>✓ all on main — nothing unmerged.</p></section>'
    items = "".join(
        f'<li><strong>{html.escape(t.get("kind", ""))}</strong>: '
        f'{html.escape(t.get("detail", ""))}</li>'
        for t in todos
    )
    return (
        '<section class="hygiene needs-attention"><h2>⚠ Needs attention</h2>'
        f"<ul>{items}</ul></section>"
    )


def _json_ld(record: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": record.get("title", record.get("slug", "")),
        "description": record.get("one_liner", ""),
        "codeRepository": record.get("repo_url", ""),
        "programmingLanguage": record.get("tech", []),
    }
    # Same <script> breakout protection as the data island: name/description are
    # LLM-authored and could contain a literal </script>.
    return json.dumps(data, indent=2, ensure_ascii=False).replace("</", "<\\/")


def _screenshot(record: dict) -> str:
    """A UI screenshot figure for human readers, or "" when none/unsafe."""
    url = record.get("screenshot_url", "")
    # Defense-in-depth: only ever emit an http(s) image src (the generator only
    # ever derives such URLs, but never trust a record blindly).
    if not url.startswith(("http://", "https://")):
        return ""
    alt = html.escape(record.get("title", record.get("slug", "")), quote=True)
    return (
        '<figure class="screenshot">'
        f'<img src="{html.escape(url, quote=True)}" alt="{alt} screenshot" loading="lazy">'
        "</figure>"
    )


def _quickstart(record: dict) -> str:
    """A 'get it running' block for human readers, or "" when none."""
    qs = record.get("quickstart", "")
    if not qs.strip():
        return ""
    return (
        '<section><h2>Quickstart</h2>'
        f'<pre class="quickstart">{html.escape(qs)}</pre></section>'
    )


def _features(record: dict) -> str:
    """A human-facing feature overview list, or "" when none."""
    feats = record.get("features", [])
    if not feats:
        return ""
    items = "".join(f"<li>{html.escape(f)}</li>" for f in feats)
    return f'<section><h2>Features</h2><ul class="features">{items}</ul></section>'


def render_page(record: dict) -> str:
    """Return a complete HTML document for *record*."""
    title = html.escape(record.get("title", record.get("slug", "")))
    thin_badge = (
        '<span class="badge thin">thin</span>' if record.get("thin") else ""
    )
    visibility = html.escape(record.get("visibility", ""))
    status = html.escape(record.get("status", ""))

    # Link to the project's own republished docs (docs/**/*.html), if any.
    docs = record.get("docs") or []
    slug_attr = html.escape(record.get("slug", ""), quote=True)
    docs_link = (
        f'<p class="docs-link"><a href="{slug_attr}/docs/">'
        f'\U0001F4C4 Project documentation '
        f'({len(docs)} doc{"" if len(docs) == 1 else "s"}) &rarr;</a></p>'
        if docs
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · davidbmar.com</title>
<script type="application/json" id="project-data">{_json_script(record)}</script>
<script type="application/ld+json">{_json_ld(record)}</script>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 920px; margin: 2rem auto;
          padding: 0 1.25rem; }}
  h1 {{ margin-bottom: .25rem; }}
  .one-liner {{ font-size: 1.15rem; opacity: .85; }}
  .badge {{ font-size: .72rem; padding: .15rem .5rem; border-radius: 999px;
            background: #ddd; color: #222; margin-left: .5rem; }}
  .badge.thin {{ background: #b88600; color: #fff; }}
  .tag {{ display: inline-block; background: #eef; color: #224; border-radius: 6px;
          padding: .1rem .45rem; margin: .1rem; font-size: .82rem; }}
  .muted {{ opacity: .5; }}
  .meta-row {{ display: flex; gap: .75rem; margin: .35rem 0; }}
  .meta-label {{ flex: 0 0 9rem; font-weight: 600; opacity: .7; }}
  /* Panels below hardcode a light background, so pin a dark text colour too —
     otherwise dark-mode (color-scheme) paints the text white => unreadable. */
  .hygiene {{ border-left: 4px solid #2a7; padding: .5rem 1rem; margin: 1.5rem 0;
              background: #f4fbf7; color: #1a1f29; }}
  .hygiene.needs-attention {{ border-color: #d33; background: #fdf4f4; }}
  .hygiene h2 {{ color: #1a1f29; }}
  pre.mermaid {{ background: #fafafa; color: #1a1f29; padding: 1rem; border-radius: 8px; }}
  pre.quickstart {{ background: #0d1117; color: #e6edf3; padding: 1rem;
                    border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }}
  figure.screenshot {{ margin: 1.5rem 0; }}
  figure.screenshot img {{ max-width: 100%; height: auto; border-radius: 10px;
                           border: 1px solid #0001; box-shadow: 0 2px 12px #0002; }}
  ul.features li {{ margin: .25rem 0; }}
  a {{ color: #2563eb; }}
  .docs-link a {{ display: inline-block; margin-top: .35rem; background: #2563eb;
                  color: #fff; padding: .4rem .85rem; border-radius: 8px;
                  text-decoration: none; font-weight: 600; }}
</style>
</head>
<body>
<header>
  <h1>{title}{thin_badge}</h1>
  <p class="one-liner">{html.escape(record.get("one_liner", ""))}</p>
  <p><a href="{html.escape(record.get("repo_url", ""))}">{html.escape(record.get("repo_url", ""))}</a>
     &nbsp;·&nbsp; {visibility} &nbsp;·&nbsp; {status}</p>
  {docs_link}
</header>

{_screenshot(record)}

<section><h2>What it is</h2><p>{html.escape(record.get("what_it_is", ""))}</p></section>

{_features(record)}

{_quickstart(record)}

<section><h2>Architecture</h2>
  <pre class="mermaid">{_mermaid(record.get("diagram_architecture", ""))}</pre>
</section>

<section><h2>How it's built</h2><p>{html.escape(record.get("how_its_built", ""))}</p></section>

<section><h2>How it runs</h2>
  <pre class="mermaid">{_mermaid(record.get("diagram_sequence", ""))}</pre>
</section>

<section><h2>How to apply &amp; reuse</h2><p>{html.escape(record.get("how_to_apply", ""))}</p></section>

<section><h2>At a glance</h2>
  {_meta_row("Capabilities", record.get("capabilities", []))}
  {_meta_row("Components", record.get("components", []))}
  {_meta_row("Tech", record.get("tech", []))}
  {_meta_row("Depends on", record.get("depends_on", []))}
  {_meta_row("Integrates with", record.get("integrates_with", []))}
  {_meta_row("Patterns", record.get("patterns", []))}
  {_meta_row("Reuse tags", record.get("reuse_tags", []))}
</section>

{_hygiene_panel(record)}

<footer class="muted">
  <p>Generated {html.escape(record.get("generated_at", ""))} ·
     commit {html.escape(record.get("source_commit", ""))} ·
     model {html.escape(record.get("model", ""))}</p>
</footer>

<script type="module">
  import mermaid from "{_MERMAID_CDN}";
  mermaid.initialize({{ startOnLoad: true }});
</script>
</body>
</html>
"""


def _index_card(p: dict) -> str:
    """One project card (server-rendered, no JS) linking to its detail page."""
    slug = p.get("slug", "")
    title = html.escape(p.get("title") or slug)
    thin = '<span class="badge thin">thin</span>' if p.get("thin") else ""
    todos = p.get("todos") or []
    if todos:
        hyg = f'<span class="hyg warn">⚠ {len(todos)} need attention</span>'
    else:
        hyg = '<span class="hyg ok">✓ all on main</span>'
    tech = _tags((p.get("tech") or [])[:4])
    shot = ""
    url = p.get("screenshot_url", "")
    if url.startswith(("http://", "https://")):
        shot = (
            f'<img class="thumb" src="{html.escape(url, quote=True)}" '
            f'alt="{title} screenshot" loading="lazy">'
        )
    pushed = p.get("pushed_at") or ""
    date_lbl = (
        f'<span class="date">{html.escape(pushed[:10])}</span>' if pushed else ""
    )
    docs_badge = (
        ' <span class="docs-badge" title="Has documentation">\U0001F4C4 docs</span>'
        if p.get("docs")
        else ""
    )
    name_attr = html.escape((p.get("title") or slug).lower(), quote=True)
    return (
        f'<a class="card" href="{html.escape(slug, quote=True)}.html" '
        f'data-pushed="{html.escape(pushed, quote=True)}" data-name="{name_attr}">'
        f"{shot}"
        f'<div class="card-body"><h2>{title}{thin}</h2>'
        f'<p class="ol">{html.escape(p.get("one_liner", ""))}</p>'
        f'<div class="tags">{tech}</div>'
        f'<div class="card-foot">{hyg}{docs_badge}{date_lbl}</div></div></a>'
    )


def render_index_page(projects: list[dict]) -> str:
    """Render the listing page over all generated project docs (server-rendered)."""
    count = len(projects)
    if projects:
        # Newest first by default — surfaces the latest repo immediately instead
        # of burying it in an alphabetical list.
        ordered = sorted(
            projects, key=lambda p: (p.get("pushed_at") or ""), reverse=True
        )
        cards = "\n".join(_index_card(p) for p in ordered)
        controls = (
            '<div class="controls">Sort: '
            '<button class="sort-btn active" data-sort="newest">Newest</button>'
            '<button class="sort-btn" data-sort="name">Name A–Z</button>'
            "</div>"
        )
        body = f'{controls}<div class="grid">{cards}</div>'
    else:
        body = '<p class="muted">No project docs generated yet.</p>'

    # Plain (non-f) string so its braces need no escaping inside the f-string.
    sort_script = """<script>
  (function () {
    var grid = document.querySelector('.grid');
    if (!grid) return;
    var cards = Array.prototype.slice.call(grid.querySelectorAll('.card'));
    function sortBy(mode) {
      cards.sort(function (a, b) {
        if (mode === 'name') {
          return (a.dataset.name || '').localeCompare(b.dataset.name || '');
        }
        return (b.dataset.pushed || '').localeCompare(a.dataset.pushed || '');
      });
      cards.forEach(function (c) { grid.appendChild(c); });
    }
    document.querySelectorAll('.sort-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.sort-btn').forEach(function (b) {
          b.classList.remove('active');
        });
        btn.classList.add('active');
        sortBy(btn.dataset.sort);
      });
    });
  })();
</script>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Project Docs · davidbmar.com</title>
<meta name="description" content="AI-generated documentation for {count} projects.">
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 1080px; margin: 2rem auto;
          padding: 0 1.25rem; }}
  header.top {{ margin-bottom: 1.5rem; }}
  header.top h1 {{ margin-bottom: .15rem; }}
  .sub {{ opacity: .7; }}
  .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
  .card {{ display: flex; flex-direction: column; border: 1px solid #8884; border-radius: 12px;
           overflow: hidden; text-decoration: none; color: inherit; background: #fff1;
           transition: box-shadow .15s, transform .15s; }}
  .card:hover {{ box-shadow: 0 6px 24px #0003; transform: translateY(-2px); }}
  .thumb {{ width: 100%; height: 150px; object-fit: cover; border-bottom: 1px solid #8883; }}
  .card-body {{ padding: .85rem 1rem 1rem; display: flex; flex-direction: column; gap: .4rem; flex: 1; }}
  .card h2 {{ font-size: 1.05rem; margin: 0; }}
  .ol {{ font-size: .9rem; opacity: .85; margin: 0; flex: 1; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: .2rem; }}
  .tag {{ background: #eef; color: #224; border-radius: 6px; padding: .05rem .4rem; font-size: .75rem; }}
  .badge.thin {{ font-size: .65rem; padding: .1rem .4rem; border-radius: 999px;
                 background: #b88600; color: #fff; margin-left: .4rem; vertical-align: middle; }}
  .hyg {{ font-size: .78rem; }}
  .hyg.ok {{ color: #2a7; }}
  .hyg.warn {{ color: #d33; }}
  .muted {{ opacity: .6; }}
  .card-foot {{ display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }}
  .date {{ font-size: .72rem; opacity: .6; margin-left: auto;
           font-variant-numeric: tabular-nums; }}
  .docs-badge {{ font-size: .72rem; color: #2563eb; }}
  .controls {{ margin: 0 0 1rem; font-size: .85rem; opacity: .85; }}
  .sort-btn {{ font: inherit; margin-left: .4rem; padding: .2rem .6rem;
               border: 1px solid #8884; border-radius: 999px; background: transparent;
               color: inherit; cursor: pointer; }}
  .sort-btn.active {{ background: #2563eb; color: #fff; border-color: #2563eb; }}
  a.home {{ color: #2563eb; }}
  .llms {{ margin-top: 2rem; padding: .9rem 1.1rem; border: 1px dashed #8886;
           border-radius: 10px; font-size: .9rem; opacity: .9; }}
  .llms a {{ color: #2563eb; }}
</style>
</head>
<body>
<header class="top">
  <h1>Project Docs</h1>
  <p class="sub">AI-generated documentation — {count} project{"" if count == 1 else "s"}.
     <a class="home" href="/">← back to portfolio search</a></p>
</header>
{body}
<aside class="llms">
  🤖 <strong>For LLMs / AI agents:</strong> start at
  <a href="/llms.txt">/llms.txt</a> — a tiny manifest that points to a compact
  machine-readable index (<a href="/data/projects-index.json">/data/projects-index.json</a>)
  and per-repo records, so you can find what you need without loading everything.
</aside>
{sort_script}
</body>
</html>
"""


def _doc_title(rel: str) -> str:
    """A readable label for a doc path like ``business/roadmap.html``."""
    name = rel.rsplit("/", 1)[-1]
    if name.lower().endswith(".html"):
        name = name[: -len(".html")]
    words = [w for w in re.split(r"[-_\s]+", name) if w]
    return " ".join(w[:1].upper() + w[1:] for w in words) or rel


def render_docs_index_page(record: dict, rels: list[str]) -> str:
    """Render the per-project docs index (``projects/<slug>/docs/index.html``).

    *rels* are doc paths relative to the docs directory (e.g.
    ``business/roadmap.html``), which is exactly how they're written to disk.
    """
    slug = record.get("slug", "")
    title = html.escape(record.get("title") or slug)
    slug_attr = html.escape(slug, quote=True)
    # Root-absolute links so this exact page renders correctly whether it is
    # served at /projects/<slug>/docs/ (index.html) OR /projects/<slug>/docs
    # (the flat docs.html copy the CF .html-rewrite resolves to).
    base = f"/projects/{slug_attr}/docs/"
    if rels:
        items = "\n".join(
            f'<li><a href="{base}{html.escape(r, quote=True)}">{html.escape(_doc_title(r))}</a>'
            f'<span class="path">{html.escape(r)}</span></li>'
            for r in rels
        )
        list_html = f'<ul class="doc-list">{items}</ul>'
    else:
        list_html = '<p class="muted">No documents.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Docs · davidbmar.com</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 820px; margin: 2rem auto;
          padding: 0 1.25rem; }}
  h1 {{ margin-bottom: .25rem; }}
  .sub {{ opacity: .7; margin-top: 0; }}
  .doc-list {{ list-style: none; padding: 0; }}
  .doc-list li {{ border: 1px solid #8884; border-radius: 10px;
                  padding: .8rem 1rem; margin: .6rem 0; }}
  .doc-list a {{ font-weight: 600; color: #2563eb; text-decoration: none;
                 font-size: 1.05rem; }}
  .doc-list .path {{ display: block; font-size: .78rem; opacity: .55;
                     margin-top: .15rem; }}
  .muted {{ opacity: .6; }}
  nav a {{ color: #2563eb; }}
</style>
</head>
<body>
<nav><a href="/projects/{slug_attr}.html">&larr; {title}</a> &nbsp;·&nbsp;
     <a href="/projects/">All projects</a></nav>
<h1>Documentation</h1>
<p class="sub">{title}</p>
{list_html}
</body>
</html>
"""
