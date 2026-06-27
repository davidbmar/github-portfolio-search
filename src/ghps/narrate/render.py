from __future__ import annotations

import html
import re
from pathlib import Path

from ..docsgen.render import _SITE_NAV, _SITE_NAV_CSS
from .schema import NarrateValidationError

TUTORIAL_SYSTEM = (
    "You are writing an APPLIED TUTORIAL (think a readable AWS applied-architecture blog) "
    "about a body of related work, for a developer who wants to learn the principles and reuse them. "
    "Output ONE JSON object: summary (string), narrative (string: what was built and why, no raw code "
    "dumps), principles (array), patterns (array), applied_examples (array: concrete ways to apply this), "
    "pitfalls (array). Ground everything in the provided PR facts. No marketing. JSON only."
)
_PROSE_KEYS = ("summary", "narrative", "principles", "patterns", "applied_examples", "pitfalls")


def write_tutorial_prose(theme: dict, prs: list[dict], client, *, model: str, retries: int = 2) -> dict:
    member_keys = set(theme.get("pr_numbers", []))
    members = [p for p in prs if f"{p['repo']}#{p['pr_number']}" in member_keys]
    facts = "\n".join(
        f"- PR#{p['pr_number']}: {p.get('problem','')} | approach: {p.get('approach','')} | "
        f"pattern: {p.get('reusable_pattern')}" for p in members
    )
    user = f"Theme: {theme.get('title','')}\nRepos: {', '.join(theme.get('repos', []))}\nPR facts:\n{facts}"
    last_missing = None
    for _ in range(retries):
        llm = client.complete_json(TUTORIAL_SYSTEM, user)
        missing = [k for k in _PROSE_KEYS if k not in llm]
        if not missing:
            for k in _PROSE_KEYS:
                theme[k] = llm[k]
            theme["model"] = model
            return theme
        last_missing = missing
    raise NarrateValidationError(f"tutorial missing fields: {last_missing}")


_LABEL_KEYS = ("name", "scenario", "title", "pattern", "principle")
_BODY_KEYS = ("description", "application", "detail", "body", "summary")


def _li(item) -> str:
    """Render one list item. Qwen sometimes returns structured objects
    (e.g. {name, description} for patterns, {scenario, application} for
    how-to-apply) instead of plain strings; render those as a labelled bullet
    rather than dumping the dict repr."""
    if isinstance(item, dict):
        label = next((item[k] for k in _LABEL_KEYS if item.get(k)), None)
        body = next((item[k] for k in _BODY_KEYS if item.get(k)), None)
        if label and body:
            return f"<li><strong>{html.escape(str(label))}</strong> — {html.escape(str(body))}</li>"
        # Unrecognised dict shape: join its values rather than show {'k': 'v'}.
        return f"<li>{html.escape(' — '.join(str(v) for v in item.values()))}</li>"
    return f"<li>{html.escape(str(item))}</li>"


def _ul(items) -> str:
    return '<ul class="bullets">' + "".join(_li(i) for i in items) + "</ul>" if items else ""


def _cards(items) -> str:
    """Patterns / how-to-apply come back as structured {label, body} objects
    (e.g. {name, description}, {scenario, application}). Render them as
    left-accent cards — the site's panel idiom — not flat bullets."""
    if not items:
        return ""
    out = []
    for it in items:
        if isinstance(it, dict):
            label = next((it[k] for k in _LABEL_KEYS if it.get(k)), "")
            body = next((it[k] for k in _BODY_KEYS if it.get(k)), "")
            if not body:  # unrecognised dict shape: fold values into the body
                body = " — ".join(str(v) for v in it.values())
        else:
            label, body = "", str(it)
        head = f"<h3>{html.escape(str(label))}</h3>" if label else ""
        out.append(f'<li class="card">{head}<p>{html.escape(str(body))}</p></li>')
    return '<ul class="cards">' + "".join(out) + "</ul>"


def _learn_chip(repo: str) -> str:
    r = html.escape(str(repo))
    return f'<a class="tag" href="/projects/{r}.html">{r}</a>'


_LEARN_CSS = """
  :root { color-scheme: light dark; }
  body { font: 16px/1.6 system-ui, sans-serif; max-width: 820px; margin: 2rem auto;
         padding: 0 1.25rem; }
  a { color: #2563eb; }
  .eyebrow { text-transform: uppercase; letter-spacing: .09em; font-size: .72rem;
             font-weight: 700; color: #2563eb; margin: 0 0 .4rem; }
  h1 { margin: 0 0 .35rem; line-height: 1.15; font-size: 2rem; }
  .lede { font-size: 1.18rem; line-height: 1.5; opacity: .9; margin: .2rem 0 .7rem; }
  .repo-chips { margin: .3rem 0 0; }
  .tag { display: inline-block; background: #eef; color: #224; border-radius: 999px;
         padding: .12rem .62rem; margin: .14rem .18rem 0 0; font-size: .8rem;
         text-decoration: none; }
  .toc { border: 1px solid #8884; border-radius: 12px; padding: .65rem 1rem;
         margin: 1.5rem 0; font-size: .9rem; }
  .toc b { display: block; text-transform: uppercase; letter-spacing: .07em;
           font-size: .68rem; opacity: .55; margin-bottom: .35rem; }
  .toc a { display: inline-block; margin: 0 1rem .15rem 0; }
  section.learn { margin: 2.1rem 0; }
  section.learn > h2 { font-size: 1.3rem; border-bottom: 1px solid #8883;
                       padding-bottom: .3rem; margin: 0 0 .8rem; }
  .narrative { font-size: 1.03rem; }
  ul.bullets { padding-left: 1.15rem; margin: .4rem 0; }
  ul.bullets li { margin: .4rem 0; }
  ul.cards { list-style: none; padding: 0; margin: 0; display: grid; gap: .75rem; }
  ul.cards li.card { border-left: 4px solid #2563eb; background: #eef3ff;
                     color: #1a1f29; border-radius: 0 10px 10px 0; padding: .65rem 1rem; }
  .card h3 { margin: 0 0 .25rem; font-size: 1rem; color: #1a1f29; }
  .card p { margin: 0; color: #1a1f29; }
  footer.prov { margin-top: 2.6rem; border-top: 1px solid #8883; padding-top: .8rem;
                font-size: .82rem; opacity: .6; }
"""


def render_learn_html(theme: dict) -> str:
    t = html.escape(theme.get("title", ""))
    repos = theme.get("repos", [])
    chips = "".join(_learn_chip(r) for r in repos)
    n_prs = len(theme.get("pr_numbers", []))
    narrative = html.escape(theme.get("narrative", ""))

    blocks = [
        ("why", "Why", "What was built &amp; why",
         f'<p class="narrative">{narrative}</p>' if narrative else ""),
        ("principles", "Principles", "Principles", _ul(theme.get("principles", []))),
        ("patterns", "Patterns", "Patterns", _cards(theme.get("patterns", []))),
        ("apply", "How to apply", "How to apply", _cards(theme.get("applied_examples", []))),
        ("pitfalls", "Pitfalls", "Pitfalls", _ul(theme.get("pitfalls", []))),
    ]
    present = [b for b in blocks if b[3]]
    sections = "".join(
        f'<section class="learn" id="{sid}"><h2>{h2}</h2>{inner}</section>'
        for sid, _nav, h2, inner in present
    )
    toc = "".join(f'<a href="#{sid}">{nav}</a>' for sid, nav, _h2, _inner in present)
    toc_html = f'<nav class="toc"><b>On this page</b>{toc}</nav>' if toc else ""

    prov = (f"Generated from {n_prs} PR{'' if n_prs == 1 else 's'}"
            f"{' across ' + html.escape(', '.join(repos)) if repos else ''}"
            f" · model {html.escape(str(theme.get('model', '') or '—'))}"
            f"{' · ' + html.escape(str(theme.get('generated_at', ''))) if theme.get('generated_at') else ''}")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t} · Learn · davidbmar.com</title>
<meta name="description" content="{html.escape(theme.get('summary', '')[:160])}">
<style>
{_LEARN_CSS}
  {_SITE_NAV_CSS}
</style>
</head>
<body>
{_SITE_NAV}
<header>
  <p class="eyebrow">Deep dive</p>
  <h1>{t}</h1>
  <p class="lede">{html.escape(theme.get('summary', ''))}</p>
  <div class="repo-chips">{chips}</div>
</header>
{toc_html}
{sections}
<footer class="prov">{prov} · <a href="/daily/">← Back to Daily</a></footer>
</body>
</html>"""


def write_learn_pages(themes: list[dict], out_dir: str | Path) -> list[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    cards = []
    for t in themes:
        slug = t["slug"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
            raise NarrateValidationError(f"unsafe slug: {slug!r}")
        p = out / f"{slug}.html"
        p.write_text(render_learn_html(t))
        written.append(str(p))
        cards.append(f'<li><a href="{html.escape(slug)}.html">{html.escape(t.get("title",""))}</a> '
                     f'— {html.escape(t.get("summary",""))}</li>')
    idx = out / "index.html"
    idx.write_text(_render_learn_index(themes), encoding="utf-8")
    written.append(str(idx))
    return written


def _render_learn_index(themes: list[dict]) -> str:
    cards = []
    for t in themes:
        slug = html.escape(t["slug"])
        repos = "".join(_learn_chip(r) for r in t.get("repos", []))
        cards.append(
            f'<li class="idx-card"><a class="idx-title" href="{slug}.html">'
            f'{html.escape(t.get("title", ""))}</a>'
            f'<p class="idx-sum">{html.escape(t.get("summary", ""))}</p>'
            f'<div class="repo-chips">{repos}</div></li>'
        )
    grid = (f'<ul class="idx-grid">{"".join(cards)}</ul>' if cards
            else '<p class="lede">No deep dives published yet.</p>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Learn · davidbmar.com</title>
<meta name="description" content="Applied, code-grounded deep dives generated from merged pull requests.">
<style>
{_LEARN_CSS}
  ul.idx-grid {{ list-style: none; padding: 0; margin: 1.6rem 0; display: grid; gap: 1rem; }}
  li.idx-card {{ border: 1px solid #8884; border-radius: 12px; padding: 1rem 1.2rem; }}
  a.idx-title {{ font-weight: 700; font-size: 1.12rem; text-decoration: none; }}
  .idx-sum {{ margin: .4rem 0 .55rem; opacity: .82; }}
  {_SITE_NAV_CSS}
</style>
</head>
<body>
{_SITE_NAV}
<header>
  <p class="eyebrow">Learn</p>
  <h1>Applied deep dives</h1>
  <p class="lede">In-depth, code-grounded tutorials generated from merged pull requests, grouped by theme.</p>
</header>
{grid}
</body>
</html>"""
