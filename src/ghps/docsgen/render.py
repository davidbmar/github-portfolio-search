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

_MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"


def _mermaid(src: str) -> str:
    """Make Mermaid source safe to embed raw in <pre> without breaking rendering.

    Escapes only ``<`` (to ``&lt;``) so a payload like ``</pre><script>`` cannot
    break out of the <pre> element. Mermaid arrow syntax contains no ``<``, and
    the browser decodes ``&lt;`` back to ``<`` in textContent before Mermaid reads
    it, so legitimate diagrams are unaffected.
    """
    return src.replace("<", "&lt;")


def _json_script(data) -> str:
    """Serialize *data* for embedding inside a <script> tag without breakout."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


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
  .hygiene {{ border-left: 4px solid #2a7; padding: .5rem 1rem; margin: 1.5rem 0;
              background: #f4fbf7; }}
  .hygiene.needs-attention {{ border-color: #d33; background: #fdf4f4; }}
  pre.mermaid {{ background: #fafafa; padding: 1rem; border-radius: 8px; }}
  pre.quickstart {{ background: #0d1117; color: #e6edf3; padding: 1rem;
                    border-radius: 8px; overflow-x: auto; white-space: pre-wrap; }}
  figure.screenshot {{ margin: 1.5rem 0; }}
  figure.screenshot img {{ max-width: 100%; height: auto; border-radius: 10px;
                           border: 1px solid #0001; box-shadow: 0 2px 12px #0002; }}
  ul.features li {{ margin: .25rem 0; }}
  a {{ color: #2563eb; }}
</style>
</head>
<body>
<header>
  <h1>{title}{thin_badge}</h1>
  <p class="one-liner">{html.escape(record.get("one_liner", ""))}</p>
  <p><a href="{html.escape(record.get("repo_url", ""))}">{html.escape(record.get("repo_url", ""))}</a>
     &nbsp;·&nbsp; {visibility} &nbsp;·&nbsp; {status}</p>
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
